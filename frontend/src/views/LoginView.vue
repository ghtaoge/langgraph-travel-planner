<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const username = ref('')
const password = ref('')

async function handleLogin() {
  const success = await authStore.login(username.value, password.value)
  if (success) {
    router.push('/chat')
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-icon">🌍</div>
      <h2>旅游规划助手</h2>
      <p class="login-desc">登录以开始规划旅程</p>

      <form @submit.prevent="handleLogin" class="login-form">
        <input v-model="username" placeholder="用户名" autocomplete="username" />
        <input v-model="password" type="password" placeholder="密码" autocomplete="current-password" />
        <button type="submit">登录</button>
      </form>

      <div v-if="authStore.loginError" class="error-msg">{{ authStore.loginError }}</div>

      <p class="register-link">
        没有账号？<router-link to="/register">注册</router-link>
      </p>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
}
.login-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 32px 40px;
  width: 360px;
  text-align: center;
}
.login-icon { font-size: 40px; margin-bottom: 12px; }
.login-card h2 { font-size: 20px; color: var(--text-primary); margin-bottom: 6px; }
.login-desc { font-size: 13px; color: var(--text-secondary); margin-bottom: 20px; }
.login-form { display: flex; flex-direction: column; gap: 10px; }
.login-form input {
  padding: 10px 14px; border: 1px solid var(--border-color); border-radius: 8px;
  background: var(--bg-primary); color: var(--text-primary); font-size: 14px;
}
.login-form input:focus { border-color: var(--accent-color); outline: none; }
.login-form button {
  padding: 12px; background: var(--accent-color); color: white; border: none;
  border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 500;
}
.error-msg { color: #ef4444; font-size: 13px; margin-top: 10px; }
.register-link { font-size: 13px; color: var(--text-secondary); margin-top: 14px; }
.register-link a { color: var(--accent-color); }
</style>
