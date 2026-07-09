<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore, useConversationsStore } from '@/stores'
import type { ThemeMode } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const convStore = useConversationsStore()
const showSidebar = computed(() => route.meta.requiresAuth !== false && authStore.isLoggedIn)
const sidebarCollapsed = ref(localStorage.getItem('sidebar_collapsed') === 'true')
const sidebarWidth = ref(Number(localStorage.getItem('sidebar_width')) || 280)
const isResizing = ref(false)
const minSidebarWidth = 220
const maxSidebarWidth = 420

onMounted(async () => {
  if (authStore.isLoggedIn) {
    if (!authStore.currentUser) await authStore.fetchCurrentUser()
    await convStore.loadConversations()
  }
})

const currentTheme = computed<ThemeMode>(() => authStore.currentUser?.theme || (localStorage.getItem('theme_mode') as ThemeMode | null) || 'dark')
const themeText = computed(() => currentTheme.value === 'dark' ? '深色' : currentTheme.value === 'light' ? '浅色' : '系统')
const themeIcon = computed(() => currentTheme.value === 'dark' ? '☾' : currentTheme.value === 'light' ? '☼' : '◐')

function timeAgo(dateStr: string): string {
  const diff = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000)
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  return `${Math.floor(diff / 86400)} 天前`
}

function statusIcon(status: string): string {
  if (status === 'active') return '●'
  if (status === 'interrupted') return '◆'
  return '✓'
}

function statusText(status: string): string {
  if (status === 'active') return '处理中'
  if (status === 'interrupted') return '等待输入'
  return '已完成'
}

function selectConversation(threadId: string) {
  router.push(`/chat/${threadId}`)
}

function newChat() {
  convStore.startNewChat()
  router.push('/chat/new')
}

function openSettings(tab = '') {
  router.push(tab ? `/settings?tab=${tab}` : '/settings')
}

function logout() {
  authStore.logout()
  router.push('/login')
}

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
  localStorage.setItem('sidebar_collapsed', String(sidebarCollapsed.value))
}

function startResize(event: PointerEvent) {
  if (sidebarCollapsed.value) return
  isResizing.value = true
  const startX = event.clientX
  const startWidth = sidebarWidth.value

  function onMove(moveEvent: PointerEvent) {
    const nextWidth = Math.min(maxSidebarWidth, Math.max(minSidebarWidth, startWidth + moveEvent.clientX - startX))
    sidebarWidth.value = nextWidth
    localStorage.setItem('sidebar_width', String(nextWidth))
  }

  function onUp() {
    isResizing.value = false
    window.removeEventListener('pointermove', onMove)
    window.removeEventListener('pointerup', onUp)
  }

  window.addEventListener('pointermove', onMove)
  window.addEventListener('pointerup', onUp)
}

async function cycleTheme() {
  const order: ThemeMode[] = ['dark', 'light', 'system']
  const next = order[(order.indexOf(currentTheme.value) + 1) % order.length]
  await authStore.updateProfile({ theme: next })
}
</script>

<template>
  <router-view v-if="!showSidebar" />
  <div v-else :class="['app-layout', { resizing: isResizing }]">
    <aside
      :class="['sidebar', { collapsed: sidebarCollapsed }]"
      :style="{ width: sidebarCollapsed ? '64px' : `${sidebarWidth}px` }"
    >
      <div class="sidebar-header">
        <button class="brand-btn" title="折叠侧栏" @click="toggleSidebar">
          <span class="brand-icon">🌍</span>
          <span v-if="!sidebarCollapsed" class="brand-text">旅游规划</span>
        </button>
        <button v-if="!sidebarCollapsed" class="new-btn" @click="newChat">+ 新对话</button>
      </div>

      <button v-if="sidebarCollapsed" class="rail-btn" title="新对话" @click="newChat">+</button>

      <div v-if="!sidebarCollapsed" class="conversation-list">
        <div
          v-for="conv in convStore.conversations"
          :key="conv.id"
          :class="['conv-item', { active: conv.id === convStore.activeThreadId }]"
          @click="selectConversation(conv.id)"
        >
          <span class="conv-status">{{ statusIcon(conv.status) }}</span>
          <div class="conv-info">
            <div class="conv-title">{{ conv.title }}</div>
            <div class="conv-meta">{{ timeAgo(conv.updated_at || conv.created_at) }} · {{ statusText(conv.status) }}</div>
          </div>
        </div>
      </div>
      <div v-else class="rail-spacer"></div>

      <div class="sidebar-footer">
        <div :class="['user-card', { compact: sidebarCollapsed }]">
          <button class="avatar-button" title="用户资料" @click="openSettings('profile')">
            <img v-if="authStore.avatarUrl" :src="authStore.avatarUrl" alt="头像" />
            <span v-else class="avatar-fallback">{{ authStore.initials }}</span>
          </button>
          <div v-if="!sidebarCollapsed" class="user-text">
            <strong>{{ authStore.username }}</strong>
            <small>{{ authStore.accountLabel }}</small>
          </div>
          <div v-if="!sidebarCollapsed" class="footer-actions">
            <button class="icon-btn theme-btn" :title="`切换主题：${themeText}`" @click="cycleTheme">
              <span>{{ themeIcon }}</span>
              <span>{{ themeText }}</span>
            </button>
            <button class="icon-btn" title="设置" @click="openSettings()">⚙</button>
            <button class="logout-btn" @click="logout">退出</button>
          </div>
        </div>
        <button v-if="sidebarCollapsed" class="rail-btn" :title="`切换主题：${themeText}`" @click="cycleTheme">{{ themeIcon }}</button>
        <button v-if="sidebarCollapsed" class="rail-btn" title="设置" @click="openSettings()">⚙</button>
      </div>

      <div v-if="!sidebarCollapsed" class="resize-handle" title="拖动调整宽度" @pointerdown="startResize"></div>
    </aside>

    <main class="main-area">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.app-layout { display: flex; height: 100vh; background: var(--bg-primary); user-select: auto; }
.app-layout.resizing { cursor: col-resize; user-select: none; }
.sidebar { position: relative; border-right: 1px solid var(--border-color); display: flex; flex-direction: column; background: var(--bg-secondary); transition: width 0.2s ease; min-width: 64px; }
.sidebar.collapsed { align-items: stretch; }
.sidebar-header { min-height: 56px; padding: 12px 14px; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center; gap: 10px; }
.brand-btn { display: flex; align-items: center; gap: 8px; min-width: 0; border: none; background: transparent; color: var(--text-primary); cursor: pointer; font-weight: 700; font-size: 15px; }
.brand-icon { width: 24px; height: 24px; display: inline-flex; align-items: center; justify-content: center; }
.brand-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.new-btn { flex-shrink: 0; padding: 7px 13px; background: var(--accent-color); color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 13px; }
.rail-btn { width: 38px; height: 38px; margin: 10px auto 0; border: 1px solid var(--border-color); border-radius: 8px; background: var(--bg-tertiary); color: var(--text-primary); cursor: pointer; display: flex; align-items: center; justify-content: center; }
.rail-spacer { flex: 1; }
.conversation-list { flex: 1; overflow-y: auto; padding: 8px; }
.conv-item { display: flex; gap: 10px; padding: 10px 12px; border-radius: 8px; cursor: pointer; transition: background 0.2s, border-color 0.2s; margin-bottom: 4px; border: 1px solid transparent; }
.conv-item:hover { background: var(--bg-tertiary); }
.conv-item.active { background: var(--accent-color-light); border-color: rgba(99,102,241,0.3); }
.conv-status { font-size: 12px; flex-shrink: 0; color: var(--accent-color); line-height: 20px; }
.conv-info { flex: 1; min-width: 0; }
.conv-title { font-size: 14px; color: var(--text-primary); font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.conv-meta { font-size: 12px; color: var(--text-tertiary); margin-top: 2px; }
.sidebar-footer { min-height: 86px; padding: 12px 14px; border-top: 1px solid var(--border-color); display: flex; flex-direction: column; gap: 8px; }
.user-card { display: grid; grid-template-columns: 44px minmax(0, 1fr); grid-template-areas: 'avatar text' 'actions actions'; gap: 8px 10px; align-items: center; color: var(--text-secondary); }
.user-card.compact { display: flex; flex-direction: column; align-items: center; }
.avatar-button { grid-area: avatar; width: 44px; height: 44px; border: none; border-radius: 50%; overflow: hidden; padding: 0; background: var(--accent-color-light); cursor: pointer; flex-shrink: 0; }
.avatar-button img, .avatar-fallback { width: 100%; height: 100%; border-radius: 50%; }
.avatar-button img { object-fit: cover; display: block; }
.avatar-fallback { display: flex; align-items: center; justify-content: center; color: var(--accent-color); font-weight: 800; font-size: 16px; }
.user-text { grid-area: text; min-width: 0; display: flex; flex-direction: column; }
.user-text strong { color: var(--text-primary); font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.user-text small { color: var(--text-tertiary); font-size: 11px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.footer-actions { grid-area: actions; display: flex; align-items: center; gap: 6px; min-width: 0; }
.icon-btn, .logout-btn { height: 30px; padding: 0 9px; background: transparent; color: var(--text-tertiary); border: 1px solid var(--border-color); border-radius: 7px; cursor: pointer; font-size: 12px; display: inline-flex; align-items: center; gap: 5px; }
.theme-btn { flex: 1; justify-content: center; }
.icon-btn:hover, .logout-btn:hover, .rail-btn:hover { color: var(--text-primary); border-color: var(--accent-color); }
.resize-handle { position: absolute; top: 0; right: -4px; width: 8px; height: 100%; cursor: col-resize; z-index: 20; }
.resize-handle::after { content: ''; position: absolute; top: 50%; right: 2px; width: 3px; height: 48px; border-radius: 99px; background: transparent; transform: translateY(-50%); transition: background 0.2s; }
.resize-handle:hover::after { background: var(--accent-color); }
.main-area { flex: 1; display: flex; flex-direction: column; min-width: 0; }
</style>