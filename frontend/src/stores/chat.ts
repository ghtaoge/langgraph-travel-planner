/** Chat Store — 多对话消息管理 + SSE 事件流 + per-threadId interrupt 状态 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { sseService } from '@/services'
import { useGraphStore } from './graph'
import { useConversationsStore } from './conversations'
import type { SSEEvent, Plan, InterruptEvent, ChatMessageDB } from '@/types'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  streaming?: boolean
  meta?: Record<string, unknown>
}

interface ThreadState {
  messages: ChatMessage[]
  interruptInfo: InterruptEvent | null
  plans: Plan[]
  approveData: Record<string, unknown> | null
  streamingMessageId: string | null
  isLoading: boolean
  currentNode: string
  activeNodes: Set<string>
  tripId: string
  tripRevision: number
  trip: Record<string, unknown> | null
}

function createThreadState(): ThreadState {
  return {
    messages: [],
    interruptInfo: null,
    plans: [],
    approveData: null,
    streamingMessageId: null,
    isLoading: false,
    currentNode: '',
    activeNodes: new Set(),
    tripId: '',
    tripRevision: 0,
    trip: null,
  }
}


function normalizeInterruptNode(node: string, payload?: Record<string, unknown>): string {
  const interruptType = String(payload?.interrupt_type || '')
  if (interruptType === 'select' || payload?.plans) return 'user_select'
  if (interruptType === 'approve' || payload?.budget || payload?.itinerary) return 'user_approve'
  if (payload?.daily_plans) return 'itinerary_refine'
  return node || 'unknown'
}


function looksLikeInternalJson(content: string): boolean {
  const trimmed = content.trim()
  if (!trimmed) return false
  if (trimmed.startsWith("{") && (trimmed.includes("\"destination\"") || trimmed.includes("\"plan_id\"") || trimmed.includes("\"total_budget\""))) return true
  if (trimmed.includes("}{\"plan_id\"") || trimmed.includes("}\{\"plan_id\"")) return true
  return false
}

function formatSystemMessage(content: string): string {
  const prefix = "恢复操作:"
  if (!content.startsWith(prefix)) return content
  const raw = content.slice(prefix.length).trim()
  try {
    const data = JSON.parse(raw) as Record<string, unknown>
    if (data.selected_plan_id) return `已选择方案 #${data.selected_plan_id}`
    if (data.approval_status === "approved") return "已批准行程"
    if (data.approval_status === "rejected") return `已要求调整：${data.approval_comment || "未填写原因"}`
  } catch {
    return "已继续执行"
  }
  return "已继续执行"
}


function isUserFacingTokenNode(node: string): boolean {
  return node === "format_output"
}

export const useChatStore = defineStore('chat', () => {
  // ── Per-thread state Map ──
  const threadStates = ref<Map<string, ThreadState>>(new Map())
  const threadId = ref<string>('')
  const userId = ref<string>('')

  // ── 获取当前活跃 thread 的状态 ──
  const currentThread = computed(() => {
    const tid = threadId.value || useConversationsStore().activeThreadId
    if (!threadStates.value.has(tid)) {
      threadStates.value.set(tid, createThreadState())
    }
    return threadStates.value.get(tid)!
  })

  const messages = computed(() => currentThread.value?.messages || [])
  const isLoading = computed(() => currentThread.value?.isLoading || false)
  const interruptInfo = computed(() => currentThread.value?.interruptInfo || null)
  const plans = computed(() => currentThread.value?.plans || [])
  const approveData = computed(() => currentThread.value?.approveData || null)
  const currentNode = computed(() => currentThread.value?.currentNode || '')
  const activeNodes = computed(() => currentThread.value?.activeNodes || new Set())
  const hasInterrupt = computed(() => interruptInfo.value !== null)
  const interruptNode = computed(() => interruptInfo.value?.node || '')
  const interruptQuestion = computed(() => interruptInfo.value?.question || '')
  const tripId = computed(() => currentThread.value?.tripId || '')
  const tripRevision = computed(() => currentThread.value?.tripRevision || 0)
  const trip = computed(() => currentThread.value?.trip || null)

  // ── Thread state helpers ──

  function getThreadState(tid: string): ThreadState {
    if (!threadStates.value.has(tid)) {
      threadStates.value.set(tid, createThreadState())
    }
    return threadStates.value.get(tid)!
  }

  function hasMessagesForThread(tid: string): boolean {
    const state = threadStates.value.get(tid)
    return !!state && state.messages.length > 0
  }

  function getLastAssistantMetadata(tid: string): Record<string, unknown> | null {
    const state = threadStates.value.get(tid)
    if (!state) return null
    // 从 DB 加载的 messages 中找最后一条 assistant 消息的 metadata
    // 注意: ChatMessage 和 ChatMessageDB 不同, metadata 在 meta 字段
    for (let i = state.messages.length - 1; i >= 0; i--) {
      const msg = state.messages[i]
      if (msg.role === 'assistant' && msg.meta) {
        return msg.meta
      }
    }
    return null
  }

  function setMessagesFromDB(tid: string, dbMessages: ChatMessageDB[]) {
    const state = getThreadState(tid)
    const visibleMessages = dbMessages.filter(m => {
      if (m.role === "assistant" && !m.metadata && looksLikeInternalJson(m.content || "")) return false
      return true
    })
    state.messages = visibleMessages.map(m => ({
      id: m.id,
      role: m.role,
      content: m.role === "system" ? formatSystemMessage(m.content) : m.content,
      timestamp: new Date(m.created_at).getTime(),
      streaming: false,
      meta: m.metadata as unknown as Record<string, unknown> || undefined,
    }))
    for (let i = 0; i < visibleMessages.length; i++) {
      if (visibleMessages[i].thinking_content) {
        state.messages[i].meta = {
          ...state.messages[i].meta,
          thinking: visibleMessages[i].thinking_content,
        }
      }
    }
  }

  function restoreInterruptFromMetadata(tid: string, metadata: Record<string, unknown>) {
    const state = getThreadState(tid)
    const interruptType = metadata.interrupt_type as string
    const interruptValue = metadata.interrupt_value as Record<string, unknown> | undefined

    // 构建 InterruptEvent
    state.interruptInfo = {
      type: 'interrupt',
      node: normalizeInterruptNode(interruptType || 'unknown', interruptValue),
      question: interruptValue?.question as string || '等待输入',
    }

    // 恢复 plans 或 approveData
    if (interruptValue?.plans) {
      state.plans = interruptValue.plans as Plan[]
    }
    if (interruptValue?.itinerary || interruptValue?.budget || interruptValue?.daily_plans) {
      state.approveData = interruptValue as Record<string, unknown>
    }
    state.isLoading = false
  }

  function clearThreadMessages(tid: string) {
    threadStates.value.delete(tid)
  }

  // ── Actions ──

  function sendMessage(query: string) {
    if (hasInterrupt.value || isLoading.value) return
    const convStore = useConversationsStore()
    // 如果是新对话, 先创建 conversation
    if (convStore.activeThreadId === 'new') {
      // SSE 流中后端会创建 conversation + 返回 thread_id
      threadId.value = ''  // 让后端生成
    } else {
      threadId.value = convStore.activeThreadId
    }

    const tid = threadId.value || convStore.activeThreadId || 'new'
    const state = getThreadState(tid)

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: query,
      timestamp: Date.now(),
    }
    state.messages.push(userMsg)

    state.interruptInfo = null
    state.plans = []
    state.approveData = null
    state.isLoading = true

    const assistantMsg: ChatMessage = {
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      streaming: true,
    }
    state.messages.push(assistantMsg)
    state.streamingMessageId = assistantMsg.id

    sseService.postStream('/api/travel/stream', {
      query,
      thread_id: threadId.value || '',
    })
  }

  function sendResume(resumeData: Record<string, unknown>) {
    const tid = threadId.value || useConversationsStore().activeThreadId
    const state = getThreadState(tid)

    state.isLoading = true

    // 处理选中方案详情
    let selectedPlan: Plan | undefined = undefined
    if (resumeData.selected_plan_id) {
      selectedPlan = state.plans.find(p => p.plan_id === Number(resumeData.selected_plan_id))
    }

    state.interruptInfo = null
    state.plans = []
    state.approveData = null

    // 添加用户操作消息
    let actionText = ''
    if (resumeData.selected_plan_id) {
      actionText = selectedPlan
        ? `选择了方案 #${selectedPlan.plan_id}: ${selectedPlan.title} (${selectedPlan.style})`
        : `选择了方案 #${resumeData.selected_plan_id}`
    } else if (resumeData.approval_status === 'approved') {
      actionText = '✅ 批准了行程方案'
    } else if (resumeData.approval_status === 'rejected') {
      actionText = `❌ 需修改: ${resumeData.approval_comment || '需要调整'}`
    }

    state.messages.push({
      id: `user-${Date.now()}`,
      role: 'user',
      content: actionText,
      timestamp: Date.now(),
    })

    const assistantMsg: ChatMessage = {
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      streaming: true,
    }
    state.messages.push(assistantMsg)
    state.streamingMessageId = assistantMsg.id

    sseService.postStream('/api/travel/resume', {
      thread_id: tid,
      resume_data: resumeData,
    })
  }

  function rollback(checkpointId: string) {
    const tid = threadId.value || useConversationsStore().activeThreadId
    const state = getThreadState(tid)
    state.interruptInfo = null
    state.isLoading = true

    sseService.postStream('/api/travel/rollback', {
      thread_id: tid,
      checkpoint_id: checkpointId,
    })
  }

  function handleSSEEvent(event: SSEEvent) {
    const graphStore = useGraphStore()
    graphStore.updateFromSSE(event)

    const convStore = useConversationsStore()
    const tid = threadId.value || convStore.activeThreadId || 'new'
    const state = getThreadState(tid)

    switch (event.type) {
      case 'thread_created':
        if (event.thread_id) {
          if (event.thread_id !== tid) {
            threadStates.value.set(event.thread_id, state)
            if (tid === 'new' || tid === 'temp-new') {
              threadStates.value.delete(tid)
            }
          }
          threadId.value = event.thread_id
          // 更新 conversations store 的 activeThreadId
          convStore.activeThreadId = event.thread_id
          void convStore.loadConversations()
        }
        break

      case 'node_start':
        state.currentNode = event.node
        state.activeNodes.add(event.node)
        break

      case 'node_end':
        state.activeNodes.delete(event.node)
        state.currentNode = ''
        break

      case 'token':
        if (state.streamingMessageId) {
          const msg = state.messages.find(m => m.id === state.streamingMessageId)
          if (msg) {
            if (event.token_type === 'thinking') {
              if (!msg.meta) msg.meta = {}
              if (!msg.meta.thinking) msg.meta.thinking = ''
              msg.meta.thinking += event.content
            } else {
              if (isUserFacingTokenNode(event.node)) msg.content += event.content
            }
          }
        }
        break

      case 'interrupt':
        if (state.streamingMessageId) {
          const msg = state.messages.find(m => m.id === state.streamingMessageId)
          if (msg) {
            msg.streaming = false
            try {
              const parsed = JSON.parse(event.question)
              if (parsed.question) msg.content = parsed.question
            } catch { msg.content = event.question }
          }
        }
        const parsedInterrupt = parseInterruptQuestion(event.question)
        state.interruptInfo = { ...event, node: normalizeInterruptNode(event.node, parsedInterrupt || undefined) }
        state.isLoading = false
        tryParseInterruptQuestion(state, event.question)
        break

      case 'custom':
        break

      case 'completed':
        if (state.streamingMessageId) {
          const msg = state.messages.find(m => m.id === state.streamingMessageId)
          if (msg) {
            msg.streaming = false
            if (event.data?.final_plan) msg.content = event.data.final_plan
          }
        }
        state.streamingMessageId = null
        state.isLoading = false
        state.activeNodes.clear()
        state.currentNode = ''
        state.tripId = event.data?.trip_id || ''
        state.tripRevision = event.data?.trip_revision || 0
        state.trip = event.data?.trip || null
        break

      case 'graph_topology':
        break
    }
  }

  function parseInterruptQuestion(question: string): Record<string, unknown> | null {
    try {
      return JSON.parse(question) as Record<string, unknown>
    } catch {
      return null
    }
  }

  function tryParseInterruptQuestion(state: ThreadState, question: string) {
    const parsed = parseInterruptQuestion(question)
    if (!parsed) return
    if (parsed.question) {
      state.interruptInfo = { ...state.interruptInfo!, question: parsed.question as string }
    }
    if (parsed.plans) state.plans = parsed.plans as Plan[]
    if (parsed.itinerary || parsed.budget || parsed.daily_plans) {
      state.approveData = parsed
    }
  }

  function handleSSEError(error: Error) {
    const state = currentThread.value
    state.isLoading = false
    if (state.streamingMessageId) {
      const msg = state.messages.find(m => m.id === state.streamingMessageId)
      if (msg) {
        msg.streaming = false
        msg.content += `\n[错误: ${error.message}]`
      }
    }
  }

  function handleSSEComplete() {
    currentThread.value.isLoading = false
  }

  function initSSE() {
    sseService.setHandlers(handleSSEEvent, handleSSEError, handleSSEComplete)
  }

  function setThreadId(id: string) {
    threadId.value = id
  }

  function clearChat() {
    const tid = threadId.value
    if (tid) {
      const state = threadStates.value.get(tid)
      if (state) {
        state.messages = []
        state.interruptInfo = null
        state.plans = []
        state.approveData = null
        state.isLoading = false
        state.streamingMessageId = null
        state.activeNodes.clear()
        state.currentNode = ''
        state.tripId = ''
        state.tripRevision = 0
        state.trip = null
      }
    }
    threadId.value = ''
  }

  initSSE()

  return {
    threadStates, threadId, userId,
    messages, isLoading, interruptInfo, plans, approveData,
    currentNode, activeNodes,
    hasInterrupt, interruptNode, interruptQuestion,
    tripId, tripRevision, trip,
    sendMessage, sendResume, rollback,
    handleSSEEvent, setThreadId, clearChat, initSSE,
    hasMessagesForThread, getLastAssistantMetadata,
    setMessagesFromDB, restoreInterruptFromMetadata, clearThreadMessages,
    getThreadState,
  }
})
