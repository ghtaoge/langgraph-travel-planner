<script setup lang="ts">
import { ref, watch } from 'vue'
import { useChatStore, useHistoryStore } from '@/stores'

const chatStore = useChatStore()
const historyStore = useHistoryStore()
const isExpanded = ref(false)
const isLoading = ref(false)

watch(isExpanded, async (expanded) => {
  if (expanded) {
    isLoading.value = true
    await historyStore.loadTimeline(chatStore.threadId)
    isLoading.value = false
  }
})

function rollbackTo(cpId: string) {
  chatStore.rollback(cpId)
  isExpanded.value = false
}
</script>

<template>
  <div class="rollback-timeline">
    <button class="toggle-btn" @click="isExpanded = !isExpanded">
      {{ isExpanded ? '⏪ 关闭时间线' : '⏪ 回退时间线' }}
    </button>

    <div v-if="isExpanded" class="timeline-panel">
      <div v-if="isLoading" class="loading">加载中...</div>

      <div v-else-if="historyStore.checkpointTimeline.length === 0" class="empty">
        暂无 checkpoint 记录
      </div>

      <div v-else class="timeline-list">
        <div
          v-for="cp in historyStore.checkpointTimeline"
          :key="cp.checkpoint_id"
          class="checkpoint-item"
        >
          <div class="cp-info">
            <span class="cp-id">{{ cp.checkpoint_id.slice(0, 8) }}</span>
            <span class="cp-node">{{ cp.next_node.join(', ') || 'END' }}</span>
            <span class="cp-time">{{ cp.timestamp }}</span>
          </div>
          <button class="rollback-btn" @click="rollbackTo(cp.checkpoint_id)">
            回退到此
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.rollback-timeline {
  padding: 8px;
}

.toggle-btn {
  width: 100%;
  padding: 6px;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  transition: background 0.2s;
}

.toggle-btn:hover {
  background: var(--bg-primary);
}

.timeline-panel {
  margin-top: 8px;
  padding: 8px;
  background: var(--bg-tertiary);
  border-radius: 6px;
}

.loading,
.empty {
  text-align: center;
  padding: 12px;
  color: var(--text-tertiary);
  font-size: 12px;
}

.timeline-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.checkpoint-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 8px;
  background: var(--bg-primary);
  border-radius: 4px;
}

.cp-info {
  display: flex;
  gap: 8px;
  align-items: center;
  flex: 1;
}

.cp-id {
  font-size: 11px;
  font-family: var(--font-mono);
  color: var(--accent-color);
}

.cp-node {
  font-size: 11px;
  color: var(--text-tertiary);
}

.cp-time {
  font-size: 10px;
  color: var(--text-tertiary);
}

.rollback-btn {
  padding: 4px 8px;
  background: #f59e0b;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
}

.rollback-btn:hover {
  background: #d97706;
}
</style>
