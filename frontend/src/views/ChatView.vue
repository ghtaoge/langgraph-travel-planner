<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useChatStore, useConversationsStore } from '@/stores'
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
const inspectorOpen = ref(false)

const threadIdFromRoute = computed(() => route.params.threadId as string || 'new')

onMounted(async () => {
  chatStore.initSSE()
  if (threadIdFromRoute.value !== 'new') {
    chatStore.setThreadId(threadIdFromRoute.value)
    await convStore.switchTo(threadIdFromRoute.value)
  }
})

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

      <button
        class="inspector-toggle"
        :class="{ open: inspectorOpen, active: chatStore.isLoading }"
        :title="inspectorOpen ? '收起执行进度' : '查看执行进度'"
        @click="inspectorOpen = !inspectorOpen"
      >
        <span class="toggle-orbit"></span>
        <span class="toggle-icon">{{ inspectorOpen ? '›' : '‹' }}</span>
      </button>
      <aside :class="['chat-sidebar-info', { open: inspectorOpen }]">
        <GraphTopology />
        <ProgressPanel />
        <TraceLink />
      </aside>
    </div>
  </div>
</template>

<style scoped>
.chat-view { flex: 1; display: flex; flex-direction: column; min-height: 0; position: relative; }
.chat-header { padding: 12px 24px; border-bottom: 1px solid var(--border-color); display: flex; align-items: center; gap: 12px; flex-shrink: 0; }
.chat-header h1 { font-size: 18px; font-weight: 600; color: var(--text-primary); }
.status-badge { font-size: 12px; padding: 2px 8px; border-radius: 8px; }
.status-badge.loading { background: var(--accent-color-light); color: var(--accent-color); animation: pulse 1.5s infinite; }
.status-badge.interrupted { background: #fef3c7; color: #f59e0b; }
@keyframes pulse { 50% { opacity: 0.5; } }
.chat-content { flex: 1; display: flex; overflow: hidden; min-height: 0; position: relative; }
.chat-main { flex: 1; display: flex; flex-direction: column; min-width: 0; min-height: 0; }
.chat-sidebar-info { position: absolute; top: 0; right: 0; bottom: 0; width: 320px; border-left: 1px solid var(--border-color); background: var(--bg-secondary); overflow-y: auto; padding: 8px; transform: translateX(100%); transition: transform 0.22s ease; z-index: 10; box-shadow: -12px 0 24px rgba(0,0,0,0.18); }
.chat-sidebar-info.open { transform: translateX(0); }
.inspector-toggle {
  position: absolute;
  right: 14px;
  top: 14px;
  z-index: 12;
  width: 34px;
  height: 34px;
  padding: 0;
  border: 1px solid rgba(99,102,241,0.55);
  border-radius: 8px;
  background: linear-gradient(135deg, var(--accent-color), #22c55e);
  color: white;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  box-shadow: 0 10px 26px rgba(99,102,241,0.24);
  transition: right 0.22s ease, transform 0.18s ease, box-shadow 0.18s ease;
  overflow: hidden;
}
.inspector-toggle:hover { transform: translateY(-1px); box-shadow: 0 14px 32px rgba(99,102,241,0.34); }
.inspector-toggle.open { right: 334px; }
.toggle-orbit {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(255,255,255,0.9);
  box-shadow: 0 0 0 0 rgba(255,255,255,0.55);
}
.inspector-toggle.active .toggle-orbit { animation: ping 1.3s infinite; }
.toggle-icon { font-size: 18px; line-height: 1; transform: translateY(-1px); }
@keyframes ping { 70%, 100% { box-shadow: 0 0 0 10px rgba(255,255,255,0); } }
</style>
