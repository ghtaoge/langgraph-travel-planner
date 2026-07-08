/** Auth Store — JWT token 管理 + 用户资料 + 主题 + 验证码 */

import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { authApi } from '@/services'

export type ThemeMode = 'dark' | 'light' | 'system'
export type AccountTargetType = 'phone' | 'email'
export type VerificationPurpose = 'reset_password' | 'bind_account' | 'change_password'

export interface AuthUser {
  id: string
  username: string
  nickname: string
  phone: string
  email: string
  phone_verified: boolean
  email_verified: boolean
  avatar_url: string
  theme: ThemeMode
  created_at: string
}

function applyTheme(theme: ThemeMode) {
  const preferredDark = window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? true
  const resolved = theme === 'system' ? (preferredDark ? 'dark' : 'light') : theme
  document.documentElement.dataset.theme = resolved
  localStorage.setItem('theme_mode', theme)
}

function normalizeUser(res: any): AuthUser {
  return {
    id: res.id || res.user_id,
    username: res.username,
    nickname: res.nickname || res.username,
    phone: res.phone || '',
    email: res.email || '',
    phone_verified: res.phone_verified || false,
    email_verified: res.email_verified || false,
    avatar_url: res.avatar_url || '',
    theme: res.theme || 'dark',
    created_at: res.created_at || '',
  }
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(localStorage.getItem('jwt_token') || '')
  const currentUser = ref<AuthUser | null>(null)
  const loginError = ref<string>('')
  const profileMessage = ref<string>('')

  const isLoggedIn = computed(() => token.value !== '')
  const username = computed(() => currentUser.value?.nickname || currentUser.value?.username || '')
  const avatarUrl = computed(() => currentUser.value?.avatar_url || '')
  const accountLabel = computed(() => currentUser.value?.phone || currentUser.value?.email || currentUser.value?.username || '')
  const initials = computed(() => username.value.slice(0, 1).toUpperCase() || 'U')

  applyTheme((localStorage.getItem('theme_mode') as ThemeMode | null) || 'dark')

  function setSession(res: any) {
    token.value = res.access_token
    currentUser.value = normalizeUser(res)
    localStorage.setItem('jwt_token', res.access_token)
    applyTheme(currentUser.value.theme)
  }

  async function login(account: string, password: string) {
    loginError.value = ''
    try {
      const res = await authApi.login({ account, password })
      setSession(res)
      return true
    } catch (err: any) {
      loginError.value = err.response?.data?.detail || '登录失败'
      return false
    }
  }

  async function register(account: string, nickname: string, password: string) {
    loginError.value = ''
    try {
      const res = await authApi.register({ account, nickname, password })
      setSession(res)
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
      currentUser.value = normalizeUser(res)
      applyTheme(currentUser.value.theme)
    } catch {
      logout()
    }
  }

  async function updateProfile(data: { nickname?: string; avatar_url?: string; theme?: ThemeMode }) {
    profileMessage.value = ''
    try {
      const res = await authApi.updateProfile(data)
      currentUser.value = normalizeUser(res)
      applyTheme(currentUser.value.theme)
      profileMessage.value = '设置已保存'
      return true
    } catch (err: any) {
      profileMessage.value = err.response?.data?.detail || '保存失败'
      return false
    }
  }

  async function sendVerificationCode(data: { target_type: AccountTargetType; target: string; purpose: VerificationPurpose }) {
    profileMessage.value = ''
    loginError.value = ''
    try {
      const res = await authApi.sendVerificationCode(data)
      profileMessage.value = res.dev_code ? `验证码: ${res.dev_code}` : '验证码已发送'
      return res
    } catch (err: any) {
      const message = err.response?.data?.detail || '验证码发送失败'
      profileMessage.value = message
      loginError.value = message
      return null
    }
  }

  async function bindAccount(data: { target_type: AccountTargetType; target: string; code: string }) {
    profileMessage.value = ''
    try {
      const res = await authApi.bindAccount(data)
      currentUser.value = normalizeUser(res)
      profileMessage.value = '绑定成功'
      return true
    } catch (err: any) {
      profileMessage.value = err.response?.data?.detail || '绑定失败'
      return false
    }
  }

  async function resetPassword(account: string, code: string, newPassword: string) {
    loginError.value = ''
    try {
      await authApi.resetPassword({ account, code, new_password: newPassword })
      return true
    } catch (err: any) {
      loginError.value = err.response?.data?.detail || '密码重置失败'
      return false
    }
  }

  async function changePassword(oldPassword: string, newPassword: string, targetType: AccountTargetType, code: string) {
    profileMessage.value = ''
    try {
      await authApi.changePassword({ old_password: oldPassword, new_password: newPassword, target_type: targetType, code })
      profileMessage.value = '密码已更新'
      return true
    } catch (err: any) {
      profileMessage.value = err.response?.data?.detail || '密码修改失败'
      return false
    }
  }

  function logout() {
    token.value = ''
    currentUser.value = null
    localStorage.removeItem('jwt_token')
  }

  return {
    token, currentUser, loginError, profileMessage,
    isLoggedIn, username, avatarUrl, accountLabel, initials,
    login, register, fetchCurrentUser, updateProfile,
    sendVerificationCode, bindAccount, resetPassword, changePassword, logout,
  }
})