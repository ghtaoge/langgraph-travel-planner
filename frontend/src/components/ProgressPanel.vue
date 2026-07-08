<script setup lang="ts">
import { useGraphStore } from '@/stores'

const graphStore = useGraphStore()
</script>

<template>
  <div class="progress-panel">
    <div class="progress-header">
      <span>执行进度</span>
      <span class="progress-percent">{{ graphStore.progressPercent }}%</span>
    </div>
    <div class="progress-bar">
      <div class="progress-fill" :style="{ width: graphStore.progressPercent + '%' }"></div>
    </div>
    <div class="node-status-list">
      <div v-for="[id, status] in Object.entries(graphStore.nodeStatusMap)" :key="id" class="status-item">
        <span :class="['status-dot', `dot-${status}`]"></span>
        <span class="status-label">{{ id }}</span>
        <span class="status-text">{{ status }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.progress-panel {
  padding: 12px;
  border-top: 1px solid var(--border-color);
}

.progress-header {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.progress-percent {
  color: var(--accent-color);
  font-weight: 600;
}

.progress-bar {
  height: 6px;
  background: var(--bg-tertiary);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 12px;
}

.progress-fill {
  height: 100%;
  background: var(--accent-color);
  border-radius: 3px;
  transition: width 0.3s;
}

.node-status-list {
  max-height: 200px;
  overflow-y: auto;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 2px 0;
  font-size: 12px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.dot-idle { background: var(--border-color); }
.dot-running { background: var(--accent-color); }
.dot-completed { background: #22c55e; }
.dot-interrupted { background: #f59e0b; }
.dot-error { background: #ef4444; }

.status-label {
  color: var(--text-secondary);
  flex: 1;
}

.status-text {
  color: var(--text-tertiary);
  font-size: 11px;
}
</style>
