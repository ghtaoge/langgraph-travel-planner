/** API 请求服务 — JWT 认证拦截器 + 所有 API 函数 */

import axios from 'axios'
import type {
  ConversationSummary,
  UserProfile,
  TopologyNode,
  TopologyEdge,
  TopologySubgraph,
} from '@/types'

const api = axios.create({
  baseURL: '',
  timeout: 30000,
})

// JWT 认证拦截器 — 每次请求自动附加 Authorization header
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('jwt_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 401 响应拦截器 — 自动跳转登录页
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('jwt_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

// ── Auth API ──

export const authApi = {
  register: (data: { account: string; nickname: string; password: string }) =>
    api.post('/api/auth/register', data).then(r => r.data),
  login: (data: { account: string; password: string }) =>
    api.post('/api/auth/login', data).then(r => r.data),
  me: () =>
    api.get('/api/auth/me').then(r => r.data),
  updateProfile: (data: { nickname?: string; avatar_url?: string; theme?: 'dark' | 'light' | 'system' }) =>
    api.patch('/api/auth/me', data).then(r => r.data),
  sendVerificationCode: (data: { target_type: 'phone' | 'email'; target: string; purpose: 'reset_password' | 'bind_account' | 'change_password' }) =>
    api.post('/api/auth/verification-code', data).then(r => r.data),
  bindAccount: (data: { target_type: 'phone' | 'email'; target: string; code: string }) =>
    api.post('/api/auth/bind-account', data).then(r => r.data),
  resetPassword: (data: { account: string; code: string; new_password: string }) =>
    api.post('/api/auth/reset-password', data).then(r => r.data),
  changePassword: (data: { old_password: string; new_password: string; target_type: 'phone' | 'email'; code: string }) =>
    api.post('/api/auth/change-password', data).then(r => r.data),
}

// ── Conversations API ──

export const conversationsApi = {
  list: (page: number = 1, perPage: number = 20) =>
    api.get('/api/conversations', { params: { page, per_page: perPage } }).then(r => r.data),
  create: () =>
    api.post('/api/conversations').then(r => r.data),
  update: (id: string, data: { title?: string; status?: string }) =>
    api.patch(`/api/conversations/${id}`, data).then(r => r.data),
  delete: (id: string) =>
    api.delete(`/api/conversations/${id}`).then(r => r.data),
}

// ── Messages API ──

export const messagesApi = {
  fetch: (threadId: string) =>
    api.get(`/api/conversations/${threadId}/messages`).then(r => r.data),
}

// ── Travel API (保持原有) ──

export async function getTopology(): Promise<{
  nodes: TopologyNode[]
  edges: TopologyEdge[]
  subgraphs: TopologySubgraph[]
}> {
  const res = await api.get('/api/travel/topology')
  return res.data
}

export async function getHistory(userId: string = 'default_user'): Promise<{
  history: ConversationSummary[]
}> {
  const res = await api.get('/api/travel/history', { params: { user_id: userId } })
  return res.data
}

export async function getProfile(userId: string = 'default_user'): Promise<{
  profile: UserProfile | Record<string, never>
}> {
  const res = await api.get('/api/travel/profile', { params: { user_id: userId } })
  return res.data
}

export default api
