/** Graph Store — 图拓扑 + 节点执行状态 + 进度动画

  核心职责:
  1. 保存后端返回的图拓扑数据 (nodes/edges/subgraphs)
  2. 维护每个节点的执行状态 (idle/running/completed/interrupted)
  3. 计算整体进度百分比
*/

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  TopologyNode,
  TopologyEdge,
  TopologySubgraph,
  NodeStatus,
} from '@/types'
import type { SSEEvent } from '@/types'

export const useGraphStore = defineStore('graph', () => {
  // ── State ──
  const topologyNodes = ref<TopologyNode[]>([])
  const topologyEdges = ref<TopologyEdge[]>([])
  const subgraphs = ref<TopologySubgraph[]>([])
  const nodeStatusMap = ref<Record<string, NodeStatus>>({})
  const progress = ref(0)

  // ── Computed ──
  const completedCount = computed(() =>
    Object.values(nodeStatusMap.value).filter(s => s === 'completed').length,
  )

  const totalNodes = computed(() => topologyNodes.value.length + subgraphs.value.reduce((sum, sg) => sum + sg.nodes.length, 0))

  const progressPercent = computed(() => {
    // 优先使用 SSE custom 事件推送的 progress (后端根据节点估算)
    if (progress.value > 0) {
      return Math.round(progress.value * 100)
    }
    // fallback: 根据节点完成比例计算
    if (totalNodes.value === 0) return 0
    return Math.round((completedCount.value / totalNodes.value) * 100)
  })

  // ── Actions ──

  /** 设置拓扑数据 (从 SSE graph_topology 事件或 API 获取) */
  function setTopology(data: {
    nodes: TopologyNode[]
    edges: TopologyEdge[]
    subgraphs: TopologySubgraph[]
  }) {
    topologyNodes.value = data.nodes
    topologyEdges.value = data.edges
    subgraphs.value = data.subgraphs

    // 初始化所有节点为 idle
    const statusMap: Record<string, NodeStatus> = {}
    for (const n of data.nodes) {
      statusMap[n.id] = 'idle'
    }
    for (const sg of data.subgraphs) {
      for (const n of sg.nodes) {
        statusMap[n.id] = 'idle'
      }
    }
    nodeStatusMap.value = statusMap
  }

  /** 更新节点状态 (从 SSE 事件) */
  function updateFromSSE(event: SSEEvent) {
    switch (event.type) {
      case 'thread_created':
        // thread_id 由 chat store 处理
        break
      case 'node_start':
        nodeStatusMap.value[event.node] = 'running'
        // 如果是子图父节点, 也标记第一个子图节点为 running
        for (const sg of subgraphs.value) {
          if (sg.parent_node === event.node && sg.nodes.length > 0) {
            nodeStatusMap.value[sg.nodes[0].id] = 'running'
          }
        }
        break
      case 'node_end':
        nodeStatusMap.value[event.node] = 'completed'
        // 子图父节点完成时, 标记所有子图内部节点也为 completed
        for (const sg of subgraphs.value) {
          if (sg.parent_node === event.node) {
            for (const n of sg.nodes) {
              nodeStatusMap.value[n.id] = 'completed'
            }
          }
        }
        break
      case 'interrupt':
        nodeStatusMap.value[event.node] = 'interrupted'
        break
      case 'graph_topology':
        setTopology(event)
        break
      case 'custom':
        if (event.data?.progress) {
          progress.value = event.data.progress
        }
        break
      case 'completed':
        // 所有节点完成
        for (const key of Object.keys(nodeStatusMap.value)) {
          if (nodeStatusMap.value[key] === 'running') {
            nodeStatusMap.value[key] = 'completed'
          }
        }
        progress.value = 1
        break
    }
  }

  /** 重置所有节点状态 */
  function resetStatus() {
    for (const key of Object.keys(nodeStatusMap.value)) {
      nodeStatusMap.value[key] = 'idle'
    }
    progress.value = 0
  }

  return {
    // state
    topologyNodes,
    topologyEdges,
    subgraphs,
    nodeStatusMap,
    progress,
    // computed
    completedCount,
    totalNodes,
    progressPercent,
    // actions
    setTopology,
    updateFromSSE,
    resetStatus,
  }
})
