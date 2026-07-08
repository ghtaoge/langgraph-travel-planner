/** Chat Store — 管理对话消息、SSE 事件流、interrupt 状态 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { sseService } from '@/services'
import { useGraphStore } from './graph'
import type { SSEEvent, Plan, InterruptEvent } from '@/types'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  streaming?: boolean
  meta?: Record<string, unknown>
}

export const useChatStore = defineStore('chat', () => {
  // ── State ──
  const messages = ref<ChatMessage[]>([])
  const threadId = ref<string>('')
  const userId = ref<string>('default_user')
  const isLoading = ref(false)
  const currentNode = ref<string>('')
  const activeNodes = ref<Set<string>>(new Set())

  /** interrupt 状态 */
  const interruptInfo = ref<InterruptEvent | null>(null)

  /** 方案列表 (user_select interrupt 时填充) */
  const plans = ref<Plan[]>([])

  /** interrupt 结构化数据 (行程/预算等, approve/daily_confirm 时填充) */
  const approveData = ref<Record<string, unknown> | null>(null)

  /** 当前 token 流拼装的 assistant 消息 ID */
  let streamingMessageId: string | null = null

  // ── Computed ──
  const hasInterrupt = computed(() => interruptInfo.value !== null)
  const interruptNode = computed(() => interruptInfo.value?.node || '')
  const interruptQuestion = computed(() => interruptInfo.value?.question || '')

  // ── Actions ──

  /** 发送用户消息并启动 SSE 流 */
  function sendMessage(query: string) {
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: query,
      timestamp: Date.now(),
    }
    messages.value.push(userMsg)

    interruptInfo.value = null
    plans.value = []
    approveData.value = null
    isLoading.value = true

    const assistantMsg: ChatMessage = {
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      streaming: true,
    }
    messages.value.push(assistantMsg)
    streamingMessageId = assistantMsg.id

    // 使用 vite proxy 相对路径 (走 /api → localhost:8001 代理, 避免 CORS)
    sseService.postStream('/api/travel/stream', {
      query,
      user_id: userId.value,
      thread_id: threadId.value,
    })
  }

  /** 恢复 interrupt — 发送 resume_data */
  function sendResume(resumeData: Record<string, unknown>) {
    isLoading.value = true

    // ── 先保存选中方案详情，再清除 interrupt 状态 ──
    let selectedPlan: Plan | undefined = undefined
    if (resumeData.selected_plan_id) {
      selectedPlan = plans.value.find(p => p.plan_id === Number(resumeData.selected_plan_id))
    }

    interruptInfo.value = null
    plans.value = []
    approveData.value = null

    // 添加用户操作消息 (选择方案/批准/拒绝)
    let actionText = ''
    if (resumeData.selected_plan_id) {
      actionText = selectedPlan
        ? `选择了方案 #${selectedPlan.plan_id}: ${selectedPlan.title} (${selectedPlan.style})`
        : `选择了方案 #${resumeData.selected_plan_id}`
      // 将选中方案的详情写入系统消息，便于追溯
      if (selectedPlan) {
        messages.value.push({
          id: `system-${Date.now()}`,
          role: 'system',
          content: `📋 ${selectedPlan.title}\n风格: ${selectedPlan.style} | 预估预算: ${selectedPlan.estimated_budget || '待计算'}\n亮点:\n${(selectedPlan.highlights || []).map(h => `  • ${h}`).join('\n')}\n概览:\n${(selectedPlan.daily_overview || []).map((d: string, i: number) => `  Day${i+1}: ${d}`).join('\n')}`,
          timestamp: Date.now(),
        })
      }
    } else if (resumeData.approval_status === 'approved') {
      actionText = '✅ 批准了行程方案'
      // 批准时也保存行程详情便于追溯
      if (approveData.value) {
        const d = approveData.value as Record<string, unknown>
        const itinerary = d.itinerary as Record<string, unknown> | undefined
        const dailyPlans = (d.daily_plans || (itinerary?.daily_plans)) as Record<string, unknown>[] | undefined
        const budget = d.budget as Record<string, unknown> | undefined
        if (itinerary || dailyPlans) {
          const dest = itinerary?.destination || d.selected_plan || '旅行'
          const duration = itinerary?.duration || (dailyPlans?.length || 0)
          const budgetStr = budget?.total_budget ? ` | 预算: ${budget.total_budget}元` : ''
          let detail = `✅ 已批准: ${dest} (${duration}天)${budgetStr}\n`
          if (dailyPlans && dailyPlans.length > 0) {
            detail += dailyPlans.map((dp: Record<string, unknown>, i: number) => {
              const acts = (dp.activities as Record<string, unknown>[] || []).map(a => `  • ${(a as any).name}${(a as any).cost ? ` (${(a as any).cost}元)` : ''}`)
              return `Day${i+1}: ${acts.join('\n')}${dp.hotel_name ? `\n  🏨 ${dp.hotel_name}` : ''}${dp.transport ? `\n  🚗 ${dp.transport}` : ''}`
            }).join('\n')
          }
          messages.value.push({
            id: `system-${Date.now() + 1}`,
            role: 'system',
            content: detail,
            timestamp: Date.now(),
          })
        }
      }
    } else if (resumeData.approval_status === 'rejected') {
      actionText = `❌ 需修改: ${resumeData.approval_comment || '需要调整'}`
    }

    // 用户操作记录
    messages.value.push({
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
    messages.value.push(assistantMsg)
    streamingMessageId = assistantMsg.id

    // 使用 vite proxy 相对路径
    sseService.postStream('/api/travel/resume', {
      thread_id: threadId.value,
      resume_data: resumeData,
    })
  }

  /** 回退到指定 checkpoint */
  function rollback(checkpointId: string) {
    interruptInfo.value = null
    isLoading.value = true

    // 使用 vite proxy 相对路径
    sseService.postStream('/api/travel/rollback', {
      thread_id: threadId.value,
      checkpoint_id: checkpointId,
    })
  }

  /** 处理 SSE 事件 */
  function handleSSEEvent(event: SSEEvent) {
    const graphStore = useGraphStore()
    graphStore.updateFromSSE(event)

    switch (event.type) {
      case 'thread_created':
        // 保存后端生成的 thread_id, 用于 resume/rollback
        if (event.thread_id) {
          threadId.value = event.thread_id
        }
        break

      case 'node_start':
        currentNode.value = event.node
        activeNodes.value.add(event.node)
        break

      case 'node_end':
        activeNodes.value.delete(event.node)
        currentNode.value = ''
        break

      case 'token':
        if (streamingMessageId) {
          const msg = messages.value.find(m => m.id === streamingMessageId)
          if (msg) {
            if (event.token_type === 'thinking') {
              // DeepSeek 思考 token — 存入 meta.thinking
              if (!msg.meta) msg.meta = {}
              if (!msg.meta.thinking) msg.meta.thinking = ''
              msg.meta.thinking += event.content
            } else {
              // 正常输出 token — 逐字追加
              msg.content += event.content
            }
          }
        }
        break

      case 'interrupt':
        if (streamingMessageId) {
          const msg = messages.value.find(m => m.id === streamingMessageId)
          if (msg) {
            msg.streaming = false
            // 给 assistant 消息添加 interrupt 描述
            try {
              const parsed = JSON.parse(event.question)
              if (parsed.question) {
                msg.content = parsed.question
              }
            } catch {
              msg.content = event.question
            }
          }
        }
        interruptInfo.value = event
        isLoading.value = false

        // 尝试从 JSON question 中提取友好文本和结构化数据
        tryParseInterruptQuestion(event.question)

        break

      case 'custom':
        break

      case 'completed':
        if (streamingMessageId) {
          const msg = messages.value.find(m => m.id === streamingMessageId)
          if (msg) {
            msg.streaming = false
            // 如果有最终行程, 写入消息内容
            if (event.data?.final_plan) {
              msg.content = event.data.final_plan
            }
          }
        }
        // 如果没有 streamingMessageId, 创建一条系统消息
        if (!streamingMessageId && event.data?.final_plan) {
          messages.value.push({
            id: `system-${Date.now()}`,
            role: 'system',
            content: event.data.final_plan,
            timestamp: Date.now(),
          })
        }
        streamingMessageId = null
        isLoading.value = false
        activeNodes.value.clear()
        currentNode.value = ''
        break

      case 'graph_topology':
        // 已在上面由 graphStore 处理
        break
    }
  }

  /** 从 interrupt question 中解析 JSON — 提取友好文本 + 方案/行程等结构化数据 */
  function tryParseInterruptQuestion(question: string) {
    try {
      const parsed = JSON.parse(question)
      // 提取友好问题文本
      if (parsed.question) {
        interruptInfo.value = {
          ...interruptInfo.value!,
          question: parsed.question,
        }
      }
      // user_select: 提取方案列表
      if (parsed.plans) {
        plans.value = parsed.plans
      }
      // user_approve / daily_confirm: 保存完整结构化数据供 UI 渲染
      if (parsed.itinerary || parsed.budget || parsed.daily_plans) {
        approveData.value = parsed
      }
    } catch {
      // question 不是 JSON, 保持原始字符串作为显示文本
    }
  }

  /** SSE 错误处理 */
  function handleSSEError(error: Error) {
    isLoading.value = false
    if (streamingMessageId) {
      const msg = messages.value.find(m => m.id === streamingMessageId)
      if (msg) {
        msg.streaming = false
        msg.content += `\n[错误: ${error.message}]`
      }
    }
  }

  /** SSE 完成 */
  function handleSSEComplete() {
    isLoading.value = false
  }

  /** 初始化 SSE 事件处理器 */
  function initSSE() {
    sseService.setHandlers(handleSSEEvent, handleSSEError, handleSSEComplete)
  }

  function setThreadId(id: string) {
    threadId.value = id
  }

  function clearChat() {
    messages.value = []
    threadId.value = ''
    interruptInfo.value = null
    plans.value = []
    approveData.value = null
    isLoading.value = false
    streamingMessageId = null
    activeNodes.value.clear()
    currentNode.value = ''
  }

  initSSE()

  return {
    messages,
    threadId,
    userId,
    isLoading,
    currentNode,
    activeNodes,
    interruptInfo,
    plans,
    approveData,
    hasInterrupt,
    interruptNode,
    interruptQuestion,
    sendMessage,
    sendResume,
    rollback,
    handleSSEEvent,
    setThreadId,
    clearChat,
    initSSE,
  }
})
