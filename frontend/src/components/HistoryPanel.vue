<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useChatStore, useHistoryStore } from '@/stores'

const chatStore = useChatStore()
const historyStore = useHistoryStore()
const isExpanded = ref(false)

onMounted(() => {
  historyStore.loadHistory()
  historyStore.loadProfile()
})

async function openConversation(threadId: string) {
  await historyStore.loadConversation(threadId)
  chatStore.setThreadId(threadId)
}

function startNewChat() {
  chatStore.clearChat()
  chatStore.setThreadId('')
}
</script>

<template>
  <div class="history-panel">
    <div class="history-header">
      <button class="toggle-btn" @click="isExpanded = !isExpanded">
        {{ isExpanded ? '关闭历史' : '📜 历史对话' }}
      </button>
      <button class="new-btn" @click="startNewChat">新对话</button>
    </div>

    <div v-if="isExpanded" class="history-content">
      <!-- 用户画像 -->
      <div v-if="historyStore.userProfile && Object.keys(historyStore.userProfile).length > 0" class="profile-badge">
        <span>偏好: {{ (historyStore.userProfile as any).preferred_style }}</span>
        <span>预算: {{ (historyStore.userProfile as any).budget_level }}</span>
        <span>去过: {{ (historyStore.userProfile as any).past_trips?.join(', ') }}</span>
      </div>

      <!-- 历史对话列表 -->
      <div v-if="historyStore.conversations.length === 0" class="empty">
        暂无历史对话
      </div>

      <div v-else class="conversation-list">
        <div
          v-for="conv in historyStore.conversations"
          :key="conv.thread_id"
          class="conv-item"
          @click="openConversation(conv.thread_id)"
        >
          <span class="conv-id">{{ conv.thread_id }}</span>
          <span class="conv-dest">{{ (conv as any).destination || '未知目的地' }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.history-panel {
  padding: 8px;
  border-bottom: 1px solid var(--border-color);
}

.history-header {
  display: flex;
  gap: 8px;
}

.toggle-btn {
  flex: 1;
  padding: 6px;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
}

.new-btn {
  padding: 6px 12px;
  background: var(--accent-color);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
}

.history-content {
  margin-top: 8px;
}

.profile-badge {
  display: flex;
  gap: 8px;
  padding: 6px 8px;
  background: var(--accent-color-light);
  border-radius: 4px;
  font-size: 12px;
  color: var(--accent-color);
  margin-bottom: 8px;
}

.empty {
  text-align: center;
  padding: 12px;
  color: var(--text-tertiary);
  font-size: 12px;
}

.conversation-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.conv-item {
  display: flex;
  gap: 8px;
  padding: 6px 8px;
  background: var(--bg-tertiary);
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
}

.conv-item:hover {
  background: var(--bg-primary);
}

.conv-id {
  font-size: 11px;
  font-family: var(--font-mono);
  color: var(--text-tertiary);
}

.conv-dest {
  font-size: 12px;
  color: var(--text-secondary);
}
</style>
