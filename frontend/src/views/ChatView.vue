<script setup lang="ts">
import { onMounted, watch, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useChatStore, useConversationsStore, useAuthStore } from '@/stores'
import ChatInput from '@/components/ChatInput.vue'
import MessageList from '@/components/MessageList.vue'
import PlanSelector from '@/components/PlanSelector.vue'
import ApprovalDialog from '@/components/ApprovalDialog.vue'
import GraphTopology from '@/components/GraphTopology.vue'
import ProgressPanel from '@/components/ProgressPanel.vue'
import TraceLink from '@/components/TraceLink.vue'

const route = useRoute()
const chatStore = useChatStore()
const convStore = useConversationsStore()
const authStore = useAuthStore()

const threadIdFromRoute = computed(() => route.params.threadId as string || 'new')

onMounted(async () => {
  chatStore.initSSE()

  // 如果有具体 threadId → 加载该对话
  if (threadIdFromRoute.value !== 'new') {
    chatStore.setThreadId(threadIdFromRoute.value)
    await convStore.switchTo(threadIdFromRoute.value)
  }
})

// 路由变化时切换对话
watch(() => route.params.threadId, async (newTid) => {
  if (newTid && newTid !== 'new') {
    chatStore.setThreadId(newTid as string)
    await convStore.switchTo(newTid as string)
  } else {
    chatStore.clearChat()
  }
})
</script>

<template>
  <div class="chat-view">
    <div class="chat-header">
      <h1>🌍 旅游规划助手</h1>
      <span v-if="chatStore.isLoading" class="status-badge loading">处理中</span>
      <span v-if="chatStore.hasInterrupt" class="status-badge interrupted">等待输入</span>
    </div>

    <div class="chat-content">
      <div class="chat-main">
        <MessageList />

        <PlanSelector />
        <ApprovalDialog />

        <ChatInput />
      </div>

      <aside class="chat-sidebar-info">
        <GraphTopology />
        <ProgressPanel />
        <TraceLink />
      </aside>
    </div>
  </div>
</template>

<style scoped>
.chat-view {
  flex: 1;
  display: flex;
  flex-direction: column;
}
.chat-header {
  padding: 12px 24px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  gap: 12px;
}
.chat-header h1 { font-size: 18px; font-weight: 600; color: var(--text-primary); }
.status-badge { font-size: 12px; padding: 2px 8px; border-radius: 8px; }
.status-badge.loading { background: var(--accent-color-light); color: var(--accent-color); animation: pulse 1.5s infinite; }
.status-badge.interrupted { background: #fef3c7; color: #f59e0b; }
@keyframes pulse { 50% { opacity: 0.5; } }

.chat-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
}
.chat-sidebar-info {
  width: 280px;
  border-left: 1px solid var(--border-color);
  background: var(--bg-secondary);
  overflow-y: auto;
  padding: 8px;
}
</style>
