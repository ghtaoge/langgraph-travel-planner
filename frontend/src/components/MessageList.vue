<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useChatStore } from '@/stores'
import type { ChatMessage } from '@/stores/chat'

const chatStore = useChatStore()
const expandedThinking = ref<Set<string>>(new Set())
const listRef = ref<HTMLElement | null>(null)
const visibleMessages = computed(() => chatStore.messages.filter(isVisibleMessage))

watch(() => [visibleMessages.value.length, chatStore.isLoading, chatStore.currentNode], async () => {
  await nextTick()
  if (listRef.value) listRef.value.scrollTop = listRef.value.scrollHeight
})

function formatTime(ts: number): string {
  return new Date(ts).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

/** 判断消息是否包含结构化内容 */
function isRichContent(content: string): boolean {
  return content.includes('📋') || content.includes('📅') || content.includes('💡')
    || content.includes('Day') || content.includes('风格')
}


function looksLikeInternalJson(content: string): boolean {
  const trimmed = content.trim()
  if (!trimmed) return false
  const markers = [
    '"destination"', "'destination'",
    '"plan_id"', "'plan_id'",
    '"total_budget"', "'total_budget'",
    '"budget_breakdown"', "'budget_breakdown'",
  ]
  return trimmed.startsWith('{') && markers.some(marker => trimmed.includes(marker))
}

function isInternalAssistantJson(msg: ChatMessage): boolean {
  return msg.role === 'assistant' && looksLikeInternalJson(msg.content || '')
}

function hasVisibleContent(msg: ChatMessage): boolean {
  return Boolean(displayContent(msg).trim() || msg.meta?.thinking || msg.streaming)
}

function isVisibleMessage(msg: ChatMessage): boolean {
  return !isInternalAssistantJson(msg) && hasVisibleContent(msg)
}

function formatSystemMessage(content: string): string {
  const prefix = '恢复操作:'
  if (!content.startsWith(prefix)) return content
  const raw = content.slice(prefix.length).trim()
  try {
    const data = JSON.parse(raw) as Record<string, unknown>
    if (data.selected_plan_id) return `已选择方案 #${data.selected_plan_id}`
    if (data.approval_status === 'approved') return '已批准行程'
    if (data.approval_status === 'rejected') return `已要求调整：${data.approval_comment || '未填写原因'}`
  } catch {
    return '已继续执行'
  }
  return '已继续执行'
}

function displayContent(msg: ChatMessage): string {
  return msg.role === 'system' ? formatSystemMessage(msg.content) : msg.content
}
function toggleThinking(msgId: string) {
  if (expandedThinking.value.has(msgId)) {
    expandedThinking.value.delete(msgId)
  } else {
    expandedThinking.value.add(msgId)
  }
}

function isThinkingExpanded(msgId: string): boolean {
  return expandedThinking.value.has(msgId)
}
</script>

<template>
  <div ref="listRef" class="message-list">
    <div v-if="visibleMessages.length === 0" class="empty-state">
      <div class="empty-icon">🌍</div>
      <h2>旅游规划助手</h2>
      <p>描述您的旅行需求，开始规划</p>
      <div class="example-list">
        <div class="example-item">我想去成都玩 3 天，喜欢美食和文化</div>
        <div class="example-item">预算中等，去西安 5 日游</div>
      </div>
    </div>

    <div v-for="msg in visibleMessages" :key="msg.id" :class="['message', `msg-${msg.role}`]">
      <div class="msg-avatar">
        <span v-if="msg.role === 'user'">👤</span>
        <span v-else-if="msg.role === 'system'">📋</span>
        <span v-else>🤖</span>
      </div>
      <div class="msg-content">
        <div class="msg-time">{{ formatTime(msg.timestamp) }}</div>
        <div :class="['msg-body', { 'msg-rich': isRichContent(displayContent(msg)) }]">
          <!-- 思考过程区域 (DeepSeek reasoning_content) -->
          <div v-if="msg.meta?.thinking" class="thinking-section" @click="toggleThinking(msg.id)">
            <div class="thinking-header">
              <span class="thinking-icon">💭</span>
              <span class="thinking-label">思考过程</span>
              <span class="thinking-toggle">{{ isThinkingExpanded(msg.id) ? '▼' : '▶' }}</span>
            </div>
            <div v-if="isThinkingExpanded(msg.id)" class="thinking-content">
              {{ msg.meta.thinking as string }}
            </div>
          </div>

          <!-- 正常输出内容 -->
          <div v-if="displayContent(msg)" class="msg-text">{{ displayContent(msg) }}</div>
          <span v-if="msg.streaming && !msg.meta?.thinking && !displayContent(msg)" class="streaming-dot">●</span>
        </div>
      </div>
    </div>

    <div v-if="chatStore.isLoading && !chatStore.hasInterrupt" class="loading-bar">
      <div class="spinner-ring"></div>
      <span>{{ chatStore.currentNode ? `正在执行: ${chatStore.currentNode}` : '处理中...' }}</span>
    </div>
  </div>
</template>

<style scoped>
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
  scroll-behavior: smooth;
  min-height: 0;
}

/* ── 空状态 ── */
.empty-state {
  text-align: center;
  min-height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 32px 20px;
}
.empty-icon { font-size: 48px; margin-bottom: 16px; }
.empty-state h2 { font-size: 20px; color: var(--text-primary); font-weight: 600; margin-bottom: 8px; }
.empty-state p { color: var(--text-secondary); font-size: 14px; }
.example-list { margin-top: 16px; display: flex; flex-direction: column; gap: 8px; }
.example-item {
  background: var(--bg-tertiary);
  padding: 10px 16px;
  border-radius: 8px;
  color: var(--text-secondary);
  font-size: 13px;
  border: 1px solid var(--border-color);
}

/* ── 消息 ── */
.message {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
  animation: msgIn 0.25s ease-out;
}

.msg-avatar {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  border-radius: 10px;
  flex-shrink: 0;
}
.msg-user .msg-avatar { background: var(--accent-color-light); }
.msg-assistant .msg-avatar { background: #1a1b2e; }
.msg-system .msg-avatar { background: rgba(245,158,11,0.15); }

.msg-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.msg-body {
  padding: 12px 16px;
  border-radius: 12px;
  position: relative;
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-primary);
  white-space: pre-wrap;
  word-break: break-word;
}
.msg-user .msg-body {
  background: var(--accent-color-light);
  border: 1px solid rgba(99,102,241,0.2);
}
.msg-assistant .msg-body {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
}
.msg-system .msg-body {
  background: rgba(245,158,11,0.08);
  border: 1px solid rgba(245,158,11,0.2);
}
.msg-rich .msg-body {
  padding: 14px 18px;
}

/* ── 思考过程区域 ── */
.thinking-section {
  background: rgba(99,102,241,0.06);
  border: 1px solid rgba(99,102,241,0.15);
  border-radius: 8px;
  padding: 8px 12px;
  margin-bottom: 10px;
  cursor: pointer;
  transition: all 0.2s;
}
.thinking-section:hover {
  background: rgba(99,102,241,0.1);
}
.thinking-header {
  display: flex;
  align-items: center;
  gap: 8px;
}
.thinking-icon { font-size: 14px; }
.thinking-label {
  font-size: 12px;
  color: rgba(99,102,241,0.8);
  font-weight: 600;
  letter-spacing: 0.5px;
}
.thinking-toggle {
  font-size: 10px;
  color: rgba(99,102,241,0.5);
  margin-left: auto;
}
.thinking-content {
  margin-top: 8px;
  padding: 8px 10px;
  background: rgba(99,102,241,0.04);
  border-radius: 6px;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.6;
  font-style: italic;
  max-height: 200px;
  overflow-y: auto;
}

.msg-time {
  font-size: 11px;
  color: var(--text-tertiary);
  line-height: 1;
  padding-left: 2px;
}

.streaming-dot {
  color: var(--accent-color);
  animation: blink 1s infinite;
  font-size: 12px;
  vertical-align: middle;
}

/* ── 加载 ── */
.loading-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  color: var(--text-secondary);
  font-size: 13px;
}
.spinner-ring {
  width: 20px; height: 20px;
  border: 2px solid var(--border-color);
  border-top-color: var(--accent-color);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }
@keyframes blink { 50% { opacity: 0.2; } }
@keyframes msgIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; } }
</style>
