<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const account = ref('')
const code = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const localMessage = ref('')

const targetType = computed<'phone' | 'email'>(() => /^1[3-9]\d{9}$/.test(account.value.trim()) ? 'phone' : 'email')
const accountValid = computed(() => /^1[3-9]\d{9}$/.test(account.value.trim()) || /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(account.value.trim()))

async function sendCode() {
  localMessage.value = ''
  if (!accountValid.value) {
    localMessage.value = '请输入正确的手机号或邮箱'
    return
  }
  const res = await authStore.sendVerificationCode({ target_type: targetType.value, target: account.value.trim(), purpose: 'reset_password' })
  if (res?.dev_code) code.value = res.dev_code
}

async function resetPassword() {
  localMessage.value = ''
  if (newPassword.value.length < 8) localMessage.value = '新密码至少 8 位'
  else if (newPassword.value !== confirmPassword.value) localMessage.value = '两次输入的新密码不一致'
  if (localMessage.value) return

  const ok = await authStore.resetPassword(account.value.trim(), code.value.trim(), newPassword.value)
  if (ok) {
    localMessage.value = '密码已重置，请重新登录'
    setTimeout(() => router.replace('/login'), 800)
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-icon">🔐</div>
      <h2>找回密码</h2>
      <p class="login-desc">通过系统配置允许的手机号或邮箱验证</p>
      <div class="login-form">
        <input v-model="account" placeholder="手机号 / 邮箱" />
        <div class="code-row">
          <input v-model="code" placeholder="验证码" />
          <button type="button" :disabled="!accountValid" @click="sendCode">获取验证码</button>
        </div>
        <input v-model="newPassword" type="password" placeholder="新密码，至少 8 位" />
        <input v-model="confirmPassword" type="password" placeholder="确认新密码" />
        <button type="button" @click="resetPassword">重置密码</button>
      </div>
      <div v-if="localMessage || authStore.loginError || authStore.profileMessage" class="error-msg">{{ localMessage || authStore.loginError || authStore.profileMessage }}</div>
      <p class="register-link"><router-link to="/login">返回登录</router-link></p>
    </div>
  </div>
</template>

<style scoped>
.login-page { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: var(--bg-primary); padding: 24px; }
.login-card { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 12px; padding: 32px 40px; width: 410px; text-align: center; }
.login-icon { font-size: 38px; margin-bottom: 12px; }
h2 { font-size: 20px; margin-bottom: 6px; }
.login-desc { font-size: 13px; color: var(--text-secondary); margin-bottom: 20px; }
.login-form { display: flex; flex-direction: column; gap: 10px; }
input { padding: 10px 14px; border: 1px solid var(--border-color); border-radius: 8px; background: var(--bg-primary); color: var(--text-primary); }
button { padding: 10px 12px; background: var(--accent-color); color: white; border: none; border-radius: 8px; cursor: pointer; }
button:disabled { opacity: 0.45; cursor: not-allowed; }
.code-row { display: grid; grid-template-columns: 1fr 110px; gap: 8px; }
.error-msg { margin-top: 10px; color: var(--accent-color); font-size: 13px; }
.register-link { margin-top: 14px; font-size: 13px; }
.register-link a { color: var(--accent-color); }
</style>