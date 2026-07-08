/** API 请求服务 — 与后端 FastAPI 路径对齐 */

import axios from 'axios'
import type {
  ConversationSummary,
  UserProfile,
  CheckpointState,
  TopologyNode,
  TopologyEdge,
  TopologySubgraph,
} from '@/types'

const api = axios.create({
  baseURL: '',  // 使用 vite proxy, 不再直连后端
  timeout: 30000,
})

/** GET /api/travel/topology — 获取图拓扑 */
export async function getTopology(): Promise<{
  nodes: TopologyNode[]
  edges: TopologyEdge[]
  subgraphs: TopologySubgraph[]
}> {
  const res = await api.get('/api/travel/topology')
  return res.data
}

/** GET /api/travel/history — 对话摘要列表 */
export async function getHistory(userId: string = 'default_user'): Promise<{
  history: ConversationSummary[]
}> {
  const res = await api.get('/api/travel/history', { params: { user_id: userId } })
  return res.data
}

/** GET /api/travel/profile — 用户画像 */
export async function getProfile(userId: string = 'default_user'): Promise<{
  profile: UserProfile | Record<string, never>
}> {
  const res = await api.get('/api/travel/profile', { params: { user_id: userId } })
  return res.data
}

/** GET /api/travel/conversation/{thread_id} — 对话详情 */
export async function getConversation(threadId: string): Promise<{
  thread_id: string
  values: Record<string, unknown>
  next: string[]
}> {
  const res = await api.get(`/api/travel/conversation/${threadId}`)
  return res.data
}

/** GET /api/travel/states/{thread_id} — checkpoint 时间线 */
export async function getStates(threadId: string): Promise<{
  states: CheckpointState[]
}> {
  const res = await api.get(`/api/travel/states/${threadId}`)
  return res.data
}

export default api
