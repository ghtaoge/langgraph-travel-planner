/** Vue Router — 路由配置 + 认证守卫 */

import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import ChatView from '@/views/ChatView.vue'
import LoginView from '@/views/LoginView.vue'
import RegisterView from '@/views/RegisterView.vue'
import SettingsView from '@/views/SettingsView.vue'
import ForgotPasswordView from '@/views/ForgotPasswordView.vue'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: LoginView,
    meta: { requiresAuth: false },
  },
  {
    path: '/register',
    name: 'register',
    component: RegisterView,
    meta: { requiresAuth: false },
  },
  {
    path: '/forgot-password',
    name: 'forgotPassword',
    component: ForgotPasswordView,
    meta: { requiresAuth: false },
  },
  {
    path: '/chat',
    name: 'chatList',
    redirect: '/chat/new',
  },
  {
    path: '/chat/:threadId',
    name: 'chatThread',
    component: ChatView,
    meta: { requiresAuth: true },
  },
  {
    path: '/settings',
    name: 'settings',
    component: SettingsView,
    meta: { requiresAuth: true },
  },
  {
    path: '/',
    redirect: '/chat',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()

  // 需要认证的路由
  if (to.meta.requiresAuth !== false && !authStore.isLoggedIn) {
    next('/login')
    return
  }

  // 已登录时访问 login/register → 跳转到 chat
  if ((to.name === 'login' || to.name === 'register') && authStore.isLoggedIn) {
    next('/chat')
    return
  }

  // 首次进入需要认证的页面 → 尝试获取用户信息
  if (authStore.isLoggedIn && !authStore.currentUser) {
    await authStore.fetchCurrentUser()
  }

  next()
})

export default router
