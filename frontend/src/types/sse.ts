/** SSE 事件类型定义 — 与后端 streaming.py 协议对齐 */

/** SSE 事件基础类型 */
export type SSEEventType =
  | 'thread_created'
  | 'node_start'
  | 'node_end'
  | 'token'
  | 'interrupt'
  | 'custom'
  | 'completed'
  | 'graph_topology'

/** thread_created 事件 — 后端发送生成的 thread_id */
export interface ThreadCreatedEvent {
  type: 'thread_created'
  thread_id: string
}

/** node_start 事件 */
export interface NodeStartEvent {
  type: 'node_start'
  node: string
}

/** node_end 事件 */
export interface NodeEndEvent {
  type: 'node_end'
  node: string
  data: string
}

/** token 事件 — LLM 逐 token 输出 (包含 thinking/output 类型) */
export interface TokenEvent {
  type: 'token'
  node: string
  content: string
  token_type: 'thinking' | 'output'  // thinking = DeepSeek 思考 token, output = 正常输出 token
}

/** interrupt 事件 — human-in-the-loop 暂停 */
export interface InterruptEvent {
  type: 'interrupt'
  node: string
  question: string
}

/** custom 事件 — 工具调用状态等 */
export interface CustomEvent {
  type: 'custom'
  data: {
    status: string
    progress: number
  }
}

/** completed 事件 — 图执行完成 */
export interface CompletedEvent {
  type: 'completed'
  data: {
    final_plan: string
  }
}

/** 所有 SSE 事件联合类型 */
export type SSEEvent =
  | ThreadCreatedEvent
  | NodeStartEvent
  | NodeEndEvent
  | TokenEvent
  | InterruptEvent
  | CustomEvent
  | CompletedEvent
  | GraphTopologyEvent

/** 图拓扑事件 (首条 SSE) */
export interface GraphTopologyEvent {
  type: 'graph_topology'
  nodes: TopologyNode[]
  edges: TopologyEdge[]
  subgraphs: TopologySubgraph[]
}

export interface TopologyNode {
  id: string
  label: string
  type: 'llm' | 'subgraph' | 'send' | 'interrupt' | 'output' | 'store' | 'command' | 'react_agent'
}

export interface TopologyEdge {
  from: string
  to: string
  conditional?: boolean
  label?: string
}

export interface TopologySubgraph {
  id: string
  parent_node: string
  nodes: TopologyNode[]
  edges: TopologyEdge[]
}
