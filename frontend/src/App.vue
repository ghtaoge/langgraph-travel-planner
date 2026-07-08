<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore, useConversationsStore } from '@/stores'

const router = useRouter()
const authStore = useAuthStore()
const convStore = useConversationsStore()

onMounted(async () => {
  if (authStore.isLoggedIn) {
    await convStore.loadConversations()
  }
})

function timeAgo(dateStr: string): string {
  const now = Date.now()
  const then = new Date(dateStr).getTime()
  const diff = Math.floor((now - then) / 1000)
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`
  return `${Math.floor(diff / 86400)}天前`
}

function statusIcon(status: string): string {
  if (status === 'active') return '🔵'
  if (status === 'interrupted') return '🟡'
  return '⚪'
}

function statusText(status: string): string {
  if (status === 'active') return '处理中'
  if (status === 'interrupted') return '等待输入'
  return '已完成'
}

async function selectConversation(threadId: string) {
  router.push(`/chat/${threadId}`)
}

async function newChat() {
  convStore.startNewChat()
  router.push('/chat/new')
}

function logout() {
  authStore.logout()
  router.push('/login')
}
</script>

<template>
  <div class="app-layout">
    <!-- 左侧: DeepSeek 风格对话列表 -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <h2>🌍 旅游规划</h2>
        <button class="new-btn" @click="newChat">+ 新对话</button>
      </div>

      <div class="conversation-list">
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

      <div class="sidebar-footer">
        <div class="user-info">
          <span>{{ authStore.username }}</span>
          <button class="logout-btn" @click="logout">退出</button>
        </div>
      </div>
    </aside>

    <!-- 右侧: 路由视图 -->
    <main class="main-area">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  background: var(--bg-primary);
}

.sidebar {
  width: 280px;
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  background: var(--bg-secondary);
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sidebar-header h2 { font-size: 16px; color: var(--text-primary); font-weight: 600; }

.new-btn {
  padding: 6px 14px; background: var(--accent-color); color: white;
  border: none; border-radius: 8px; cursor: pointer; font-size: 13px;
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.conv-item {
  display: flex;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
  margin-bottom: 4px;
}

.conv-item:hover { background: var(--bg-tertiary); }
.conv-item.active { background: var(--accent-color-light); border: 1px solid rgba(99,102,241,0.3); }

.conv-status { font-size: 14px; flex-shrink: 0; }
.conv-info { flex: 1; min-width: 0; }
.conv-title { font-size: 14px; color: var(--text-primary); font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.conv-meta { font-size: 12px; color: var(--text-tertiary); margin-top: 2px; }

.sidebar-footer {
  padding: 12px 16px;
  border-top: 1px solid var(--border-color);
}

.user-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: var(--text-secondary);
}

.logout-btn {
  padding: 4px 10px; background: transparent; color: var(--text-tertiary);
  border: 1px solid var(--border-color); border-radius: 6px; cursor: pointer; font-size: 12px;
}

.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
}
</style>
