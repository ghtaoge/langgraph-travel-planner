<script setup lang="ts">
import { onMounted } from 'vue'
import { useGraphStore } from '@/stores'
import { getTopology } from '@/services'

const graphStore = useGraphStore()

onMounted(async () => {
  try {
    const topo = await getTopology()
    graphStore.setTopology(topo)
  } catch (err) {
    console.error('加载拓扑失败:', err)
  }
})

/** 节点类型 → 图标 */
function nodeIcon(type: string): string {
  const icons: Record<string, string> = {
    llm: '🧠',
    subgraph: '📦',
    send: '⚡',
    interrupt: '⏸️',
    output: '📄',
    store: '💾',
    command: '🔀',
    react_agent: '🤖',
  }
  return icons[type] || '○'
}

/** 节点状态 → CSS class */
function statusClass(nodeId: string): string {
  const status = graphStore.nodeStatusMap[nodeId] || 'idle'
  return `node-${status}`
}
</script>

<template>
  <div class="graph-topology">
    <h3>图执行拓扑</h3>

    <!-- 主图节点 -->
    <div class="topo-section">
      <div class="section-label">主图</div>
      <div class="node-grid">
        <div
          v-for="node in graphStore.topologyNodes"
          :key="node.id"
          :class="['topo-node', statusClass(node.id)]"
        >
          <span class="node-icon">{{ nodeIcon(node.type) }}</span>
          <span class="node-label">{{ node.label }}</span>
        </div>
      </div>
    </div>

    <!-- 子图 -->
    <div v-for="sg in graphStore.subgraphs" :key="sg.id" class="topo-section subgraph-section">
      <div class="section-label">子图: {{ sg.id }}</div>
      <div class="node-grid">
        <div
          v-for="node in sg.nodes"
          :key="node.id"
          :class="['topo-node', 'topo-node-small', statusClass(node.id)]"
        >
          <span class="node-icon">{{ nodeIcon(node.type) }}</span>
          <span class="node-label">{{ node.label }}</span>
        </div>
      </div>
    </div>

    <!-- 边列表 (简化) -->
    <div class="edges-section">
      <div v-for="edge in graphStore.topologyEdges" :key="`${edge.from}-${edge.to}`" class="edge-item">
        <span>{{ edge.from }}</span>
        <span class="arrow">→</span>
        <span>{{ edge.to }}</span>
        <span v-if="edge.conditional" class="cond-badge">{{ edge.label }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.graph-topology {
  padding: 12px;
  overflow-y: auto;
}

.graph-topology h3 {
  font-size: 14px;
  margin: 0 0 12px 0;
  color: var(--text-primary);
}

.topo-section {
  margin-bottom: 16px;
}

.section-label {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-bottom: 8px;
}

.node-grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.topo-node {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 6px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  transition: all 0.3s;
}

.topo-node-small {
  padding: 4px 8px;
  font-size: 12px;
}

.node-icon {
  font-size: 14px;
}

.node-label {
  font-size: 13px;
  color: var(--text-primary);
}

.node-idle {
  opacity: 0.6;
}

.node-running {
  border-color: var(--accent-color);
  background: var(--accent-color-light);
  color: var(--text-primary);
  animation: node-pulse 1s infinite;
}

.node-completed {
  border-color: #22c55e;
  opacity: 1;
}

.node-interrupted {
  border-color: #f59e0b;
  background: rgba(245, 158, 11, 0.1);
  color: var(--text-primary);
}

.subgraph-section {
  border: 1px dashed var(--border-color);
  border-radius: 6px;
  padding: 8px;
}

.edges-section {
  margin-top: 12px;
}

.edge-item {
  font-size: 11px;
  color: var(--text-tertiary);
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 0;
}

.arrow {
  color: var(--text-secondary);
}

.cond-badge {
  font-size: 10px;
  background: #fef3c7;
  padding: 1px 4px;
  border-radius: 2px;
}

@keyframes node-pulse {
  50% { opacity: 0.7; }
}
</style>
