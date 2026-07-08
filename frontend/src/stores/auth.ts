/** Auth Store — JWT token 管理 + 登录状态 + 用户信息 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/services'

export interface AuthUser {
  id: string
  username: string
  created_at: string
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(localStorage.getItem('jwt_token') || '')
  const currentUser = ref<AuthUser | null>(null)
  const loginError = ref<string>('')

  const isLoggedIn = computed(() => token.value !== '')
  const username = computed(() => currentUser.value?.username || '')

  async function login(usernameInput: string, password: string) {
    loginError.value = ''
    try {
      const res = await authApi.login({ username: usernameInput, password })
      token.value = res.access_token
      currentUser.value = { id: res.user_id, username: res.username, created_at: '' }
      localStorage.setItem('jwt_token', res.access_token)
      return true
    } catch (err: any) {
      loginError.value = err.response?.data?.detail || '登录失败'
      return false
    }
  }

  async function register(usernameInput: string, password: string) {
    loginError.value = ''
    try {
      const res = await authApi.register({ username: usernameInput, password })
      token.value = res.access_token
      currentUser.value = { id: res.user_id, username: res.username, created_at: '' }
      localStorage.setItem('jwt_token', res.access_token)
      return true
    } catch (err: any) {
      loginError.value = err.response?.data?.detail || '注册失败'
      return false
    }
  }

  async function fetchCurrentUser() {
    if (!token.value) return
    try {
      const res = await authApi.me()
      currentUser.value = res
    } catch {
      // Token 过期或无效
      logout()
    }
  }

  function logout() {
    token.value = ''
    currentUser.value = null
    localStorage.removeItem('jwt_token')
  }

  return {
    token, currentUser, loginError,
    isLoggedIn, username,
    login, register, fetchCurrentUser, logout,
  }
})
