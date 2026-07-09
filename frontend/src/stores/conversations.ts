/** ConversationManager Store — 多对话列表管理 + 消息加载/恢复 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { conversationsApi, messagesApi } from '@/services'
import { useChatStore } from './chat'
import type { Conversation, ChatMessageDB } from '@/types'

export const useConversationsStore = defineStore('conversations', () => {
  const conversations = ref<Conversation[]>([])
  const activeThreadId = ref<string>('new')
  const loading = ref(false)

  async function loadConversations() {
    loading.value = true
    try {
      const res = await conversationsApi.list(1, 50)
      conversations.value = res as Conversation[]
    } catch (err) {
      console.error('加载对话列表失败:', err)
    } finally {
      loading.value = false
    }
  }

  async function createConversation() {
    try {
      const conv = await conversationsApi.create() as Conversation
      conversations.value.unshift(conv)
      activeThreadId.value = conv.id
      return conv
    } catch (err) {
      console.error('创建对话失败:', err)
      return null
    }
  }

  async function switchTo(threadId: string) {
    activeThreadId.value = threadId
    const chatStore = useChatStore()
    chatStore.setThreadId(threadId)

    // 如果该 threadId 的消息还没加载过 → 从 DB 拉取
    if (!chatStore.hasMessagesForThread(threadId)) {
      await loadMessagesForThread(threadId)
    }

    // 如果对话是 interrupted → 从 metadata 恢复 interrupt 状态
    const conv = conversations.value.find(c => c.id === threadId)
    if (conv?.status === 'interrupted') {
      await restoreInterruptState(threadId)
    }
  }

  async function loadMessagesForThread(threadId: string) {
    const chatStore = useChatStore()
    chatStore.setThreadId(threadId)
    try {
      const dbMessages = await messagesApi.fetch(threadId) as ChatMessageDB[]
      chatStore.setMessagesFromDB(threadId, dbMessages)
    } catch (err) {
      console.error('加载消息失败:', err)
    }
  }

  async function restoreInterruptState(threadId: string) {
    const chatStore = useChatStore()
    chatStore.setThreadId(threadId)
    const metadata = chatStore.getLastAssistantMetadata(threadId)
    if (metadata) {
      chatStore.restoreInterruptFromMetadata(threadId, metadata)
    }
  }

  async function deleteConversation(threadId: string) {
    try {
      await conversationsApi.delete(threadId)
      conversations.value = conversations.value.filter(c => c.id !== threadId)
      const chatStore = useChatStore()
      chatStore.clearThreadMessages(threadId)
      if (activeThreadId.value === threadId) {
        activeThreadId.value = 'new'
      }
    } catch (err) {
      console.error('删除对话失败:', err)
    }
  }

  async function updateConversationTitle(threadId: string, title: string) {
    try {
      await conversationsApi.update(threadId, { title })
      const conv = conversations.value.find(c => c.id === threadId)
      if (conv) conv.title = title
    } catch (err) {
      console.error('更新标题失败:', err)
    }
  }

  function startNewChat() {
    activeThreadId.value = 'new'
    const chatStore = useChatStore()
    chatStore.clearChat()
  }

  return {
    conversations, activeThreadId, loading,
    loadConversations, createConversation, switchTo,
    deleteConversation, updateConversationTitle, startNewChat,
    loadMessagesForThread, restoreInterruptState,
  }
})
