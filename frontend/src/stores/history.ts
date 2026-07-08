/** History Store — 历史对话列表 + 用户画像 + Checkpoint 时间线

  核心职责:
  1. 加载历史对话列表 (Store search)
  2. 加载用户旅行画像 (Store get)
  3. 加载对话详情 (Checkpoint)
  4. 加载 checkpoint 时间线 (回退用)
*/

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getHistory, getProfile, getConversation, getStates } from '@/services'
import type {
  ConversationSummary,
  UserProfile,
  CheckpointState,
} from '@/types'

export const useHistoryStore = defineStore('history', () => {
  // ── State ──
  const conversations = ref<ConversationSummary[]>([])
  const userProfile = ref<UserProfile | Record<string, never>>({})
  const currentConversation = ref<Record<string, unknown> | null>(null)
  const checkpointTimeline = ref<CheckpointState[]>([])
  const loading = ref(false)

  // ── Actions ──

  /** 加载历史对话列表 */
  async function loadHistory(userId: string = 'default_user') {
    loading.value = true
    try {
      const res = await getHistory(userId)
      conversations.value = res.history
    } catch (err) {
      console.error('加载历史对话失败:', err)
    } finally {
      loading.value = false
    }
  }

  /** 加载用户画像 */
  async function loadProfile(userId: string = 'default_user') {
    try {
      const res = await getProfile(userId)
      userProfile.value = res.profile
    } catch (err) {
      console.error('加载用户画像失败:', err)
    }
  }

  /** 加载对话详情 */
  async function loadConversation(threadId: string) {
    loading.value = true
    try {
      const res = await getConversation(threadId)
      currentConversation.value = res.values
    } catch (err) {
      console.error('加载对话详情失败:', err)
    } finally {
      loading.value = false
    }
  }

  /** 加载 checkpoint 时间线 (回退用) */
  async function loadTimeline(threadId: string) {
    loading.value = true
    try {
      const res = await getStates(threadId)
      checkpointTimeline.value = res.states
    } catch (err) {
      console.error('加载时间线失败:', err)
    } finally {
      loading.value = false
    }
  }

  return {
    // state
    conversations,
    userProfile,
    currentConversation,
    checkpointTimeline,
    loading,
    // actions
    loadHistory,
    loadProfile,
    loadConversation,
    loadTimeline,
  }
})
