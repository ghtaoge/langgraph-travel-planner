<script setup lang="ts">
import { ref } from 'vue'
import { useChatStore } from '@/stores'

const chatStore = useChatStore()
const expandedThinking = ref<Set<string>>(new Set())

function formatTime(ts: number): string {
  return new Date(ts).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

/** 判断消息是否包含结构化内容 */
function isRichContent(content: string): boolean {
  return content.includes('📋') || content.includes('📅') || content.includes('💡')
    || content.includes('Day') || content.includes('风格')
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
  <div class="message-list">
    <div v-if="chatStore.messages.length === 0" class="empty-state">
      <div class="empty-icon">🌍</div>
      <h2>旅游规划助手</h2>
      <p>描述您的旅行需求，开始规划</p>
      <div class="example-list">
        <div class="example-item">我想去成都玩 3 天，喜欢美食和文化</div>
        <div class="example-item">预算中等，去西安 5 日游</div>
      </div>
    </div>

    <div v-for="msg in chatStore.messages" :key="msg.id" :class="['message', `msg-${msg.role}`]">
      <div class="msg-avatar">
        <span v-if="msg.role === 'user'">👤</span>
        <span v-else-if="msg.role === 'system'">📋</span>
        <span v-else>🤖</span>
      </div>
      <div :class="['msg-body', { 'msg-rich': isRichContent(msg.content) }]">
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
        <div v-if="msg.content" class="msg-text">{{ msg.content }}</div>
        <span v-if="msg.streaming && !msg.meta?.thinking && !msg.content" class="streaming-dot">●</span>
      </div>
      <div class="msg-time">{{ formatTime(msg.timestamp) }}</div>
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
}

/* ── 空状态 ── */
.empty-state {
  text-align: center;
  padding: 60px 20px;
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

.msg-body {
  flex: 1;
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
  padding-top: 4px;
  align-self: flex-end;
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
