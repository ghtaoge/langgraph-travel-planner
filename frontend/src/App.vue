<script setup lang="ts">
import { onMounted } from 'vue'
import { useChatStore } from '@/stores'
import ChatInput from '@/components/ChatInput.vue'
import MessageList from '@/components/MessageList.vue'
import PlanSelector from '@/components/PlanSelector.vue'
import ApprovalDialog from '@/components/ApprovalDialog.vue'
import GraphTopology from '@/components/GraphTopology.vue'
import ProgressPanel from '@/components/ProgressPanel.vue'
import RollbackTimeline from '@/components/RollbackTimeline.vue'
import HistoryPanel from '@/components/HistoryPanel.vue'
import TraceLink from '@/components/TraceLink.vue'

const chatStore = useChatStore()

onMounted(() => {
  chatStore.initSSE()
})
</script>

<template>
  <div class="app-layout">
    <!-- 左侧: 拓扑图 + 进度 + 历史 + 回退 -->
    <aside class="sidebar">
      <HistoryPanel />
      <GraphTopology />
      <ProgressPanel />
      <RollbackTimeline />
      <div class="sidebar-footer">
        <TraceLink />
      </div>
    </aside>

    <!-- 右侧: 聊天区 -->
    <main class="chat-area">
      <div class="chat-header">
        <h1>🌍 LangGraph 旅游规划助手</h1>
        <span class="badge">26 知识点全覆盖</span>
        <span v-if="chatStore.isLoading" class="status-badge loading">处理中</span>
        <span v-if="chatStore.hasInterrupt" class="status-badge interrupted">等待输入</span>
      </div>

      <MessageList />

      <!-- interrupt 交互区域 -->
      <PlanSelector />
      <ApprovalDialog />

      <!-- 正常输入 -->
      <ChatInput />
    </main>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  background: var(--bg-primary);
}

.sidebar {
  width: var(--sidebar-width);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  background: var(--bg-secondary);
  overflow-y: auto;
}

.sidebar-footer {
  padding: 8px;
  border-top: 1px solid var(--border-color);
}

.chat-area {
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

.chat-header h1 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.badge {
  font-size: 12px;
  background: var(--accent-color);
  color: white;
  padding: 2px 8px;
  border-radius: 8px;
}

.status-badge {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 8px;
}

.status-badge.loading {
  background: var(--accent-color-light);
  color: var(--accent-color);
  animation: pulse 1.5s infinite;
}

.status-badge.interrupted {
  background: #fef3c7;
  color: #f59e0b;
}

@keyframes pulse {
  50% { opacity: 0.5; }
}
</style>
