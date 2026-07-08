<script setup lang="ts">
import { ref } from 'vue'
import { useChatStore } from '@/stores'

const chatStore = useChatStore()
const inputText = ref('')

function handleSend() {
  if (!inputText.value.trim()) return
  chatStore.sendMessage(inputText.value.trim())
  inputText.value = ''
}
</script>

<template>
  <div class="chat-input">
    <!-- interrupt 时隐藏正常输入, 由 PlanSelector/ApprovalDialog 处理 -->
    <div v-if="chatStore.hasInterrupt" class="interrupt-waiting">
      <span>等待您的操作... 👆 请在上方选择方案或审批</span>
    </div>

    <!-- 正常输入 -->
    <div v-else class="input-row">
      <textarea
        v-model="inputText"
        :disabled="chatStore.isLoading"
        placeholder="描述你的旅行需求..."
        rows="3"
        @keydown.enter.exact="handleSend"
      ></textarea>
      <button :disabled="chatStore.isLoading || !inputText.trim()" @click="handleSend">
        {{ chatStore.isLoading ? '处理中...' : '发送' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.chat-input {
  padding: 12px 24px;
  border-top: 1px solid var(--border-color);
}

.input-row {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.input-row textarea {
  flex: 1;
  padding: 10px 16px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  font-size: 14px;
  background: var(--bg-primary);
  color: var(--text-primary);
  resize: vertical;
  min-height: 72px;
  line-height: 1.5;
  font-family: inherit;
}

.input-row button {
  padding: 10px 20px;
  height: 44px;
  background: var(--accent-color);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  align-self: flex-end;
}

.input-row button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.interrupt-waiting {
  text-align: center;
  padding: 10px;
  color: var(--text-secondary);
  font-size: 13px;
}
</style>
