<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const account = ref('')
const nickname = ref('')
const password = ref('')
const confirmPassword = ref('')
const localError = ref('')

const accountValid = computed(() => /^1[3-9]\d{9}$/.test(account.value.trim()) || /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(account.value.trim()))
const passwordValid = computed(() => password.value.length >= 8)
const canSubmit = computed(() => accountValid.value && nickname.value.trim().length > 0 && passwordValid.value && password.value === confirmPassword.value)

async function handleRegister() {
  localError.value = ''
  if (!accountValid.value) localError.value = '账号只能使用手机号或邮箱'
  else if (!nickname.value.trim()) localError.value = '请输入昵称'
  else if (!passwordValid.value) localError.value = '密码至少 8 位'
  else if (password.value !== confirmPassword.value) localError.value = '两次输入的密码不一致'
  if (localError.value) return

  const success = await authStore.register(account.value.trim(), nickname.value.trim(), password.value)
  if (success) {
    await router.replace('/chat/new')
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-icon">🌍</div>
      <h2>注册账号</h2>
      <p class="login-desc">账号用于登录，昵称用于展示</p>

      <form @submit.prevent="handleRegister" class="login-form">
        <input v-model="account" placeholder="手机号 / 邮箱" autocomplete="username" />
        <input v-model="nickname" placeholder="昵称" autocomplete="nickname" />
        <input v-model="password" type="password" placeholder="密码，至少 8 位" autocomplete="new-password" />
        <input v-model="confirmPassword" type="password" placeholder="确认密码" autocomplete="new-password" />
        <button type="submit" :disabled="!canSubmit">注册</button>
      </form>

      <div v-if="localError || authStore.loginError" class="error-msg">{{ localError || authStore.loginError }}</div>

      <p class="register-link">
        已有账号？<router-link to="/login">登录</router-link>
      </p>
    </div>
  </div>
</template>

<style scoped>
.login-page { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: var(--bg-primary); padding: 24px; }
.login-card { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 12px; padding: 32px 40px; width: 390px; text-align: center; }
.login-icon { font-size: 40px; margin-bottom: 12px; }
.login-card h2 { font-size: 20px; color: var(--text-primary); margin-bottom: 6px; }
.login-desc { font-size: 13px; color: var(--text-secondary); margin-bottom: 20px; }
.login-form { display: flex; flex-direction: column; gap: 10px; }
.login-form input { padding: 10px 14px; border: 1px solid var(--border-color); border-radius: 8px; background: var(--bg-primary); color: var(--text-primary); font-size: 14px; }
.login-form input:focus { border-color: var(--accent-color); outline: none; }
.login-form button { padding: 12px; background: var(--accent-color); color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 500; }
.login-form button:disabled { opacity: 0.45; cursor: not-allowed; }
.error-msg { color: #ef4444; font-size: 13px; margin-top: 10px; }
.register-link { font-size: 13px; color: var(--text-secondary); margin-top: 14px; }
.register-link a { color: var(--accent-color); }
</style>