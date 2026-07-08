/** 图拓扑类型 — 重导出 SSE 拓扑类型 */

export type {
  TopologyNode,
  TopologyEdge,
  TopologySubgraph,
  GraphTopologyEvent,
} from './sse'

/** 节点执行状态 */
export type NodeStatus = 'idle' | 'running' | 'completed' | 'interrupted' | 'error'

/** 节点可视化数据 — 前端渲染用 */
export interface NodeVisual {
  id: string
  label: string
  type: string
  status: NodeStatus
  x?: number
  y?: number
}

/** 边可视化数据 */
export interface EdgeVisual {
  from: string
  to: string
  conditional: boolean
  label?: string
  active: boolean
}
