<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const tabs = [
  { id: 'profile', label: '资料', icon: '👤' },
  { id: 'account', label: '账号绑定', icon: '🔐' },
  { id: 'security', label: '密码安全', icon: '🛡' },
  { id: 'preferences', label: '偏好', icon: '⚙' },
] as const

type SettingsTab = typeof tabs[number]['id']

const activeTab = ref<SettingsTab>((route.query.tab as SettingsTab) || 'profile')
const nickname = ref('')
const avatarUrl = ref('')
const bindTargetType = ref<'phone' | 'email'>('email')
const bindTarget = ref('')
const bindCode = ref('')
const passwordVerifyType = ref<'phone' | 'email'>('phone')
const passwordCode = ref('')
const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const localMessage = ref('')
const uploadInput = ref<HTMLInputElement | null>(null)

const verifyTarget = computed(() => passwordVerifyType.value === 'phone' ? authStore.currentUser?.phone : authStore.currentUser?.email)
const hasVerifiedTarget = computed(() => passwordVerifyType.value === 'phone' ? authStore.currentUser?.phone_verified : authStore.currentUser?.email_verified)

onMounted(async () => {
  if (!authStore.currentUser) await authStore.fetchCurrentUser()
  syncForm()
})

watch(() => authStore.currentUser, syncForm)
watch(() => route.query.tab, (tab) => {
  if (tabs.some(item => item.id === tab)) activeTab.value = tab as SettingsTab
})

function syncForm() {
  nickname.value = authStore.currentUser?.nickname || ''
  avatarUrl.value = authStore.currentUser?.avatar_url || ''
  if (authStore.currentUser?.phone) passwordVerifyType.value = 'phone'
  else if (authStore.currentUser?.email) passwordVerifyType.value = 'email'
}

function setTab(tab: SettingsTab) {
  activeTab.value = tab
  router.replace({ query: { tab } })
}

async function saveProfile() {
  localMessage.value = ''
  await authStore.updateProfile({ nickname: nickname.value.trim(), avatar_url: avatarUrl.value.trim() })
}

function pickAvatar() {
  uploadInput.value?.click()
}

function handleAvatarUpload(event: Event) {
  localMessage.value = ''
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (!file.type.startsWith('image/')) {
    localMessage.value = '请选择图片文件'
    return
  }
  if (file.size > 1024 * 1024) {
    localMessage.value = '图片不能超过 1MB'
    return
  }
  const reader = new FileReader()
  reader.onload = () => {
    avatarUrl.value = String(reader.result || '')
  }
  reader.readAsDataURL(file)
}

async function sendBindCode() {
  localMessage.value = ''
  if (!bindTarget.value.trim()) {
    localMessage.value = '请输入要绑定的手机号或邮箱'
    return
  }
  const res = await authStore.sendVerificationCode({ target_type: bindTargetType.value, target: bindTarget.value.trim(), purpose: 'bind_account' })
  if (res?.dev_code) bindCode.value = res.dev_code
}

async function bindAccount() {
  localMessage.value = ''
  await authStore.bindAccount({ target_type: bindTargetType.value, target: bindTarget.value.trim(), code: bindCode.value.trim() })
}

async function sendPasswordCode() {
  localMessage.value = ''
  if (!verifyTarget.value || !hasVerifiedTarget.value) {
    localMessage.value = '请先绑定并验证该方式'
    return
  }
  const res = await authStore.sendVerificationCode({ target_type: passwordVerifyType.value, target: verifyTarget.value, purpose: 'change_password' })
  if (res?.dev_code) passwordCode.value = res.dev_code
}

async function savePassword() {
  localMessage.value = ''
  if (newPassword.value.length < 8) {
    localMessage.value = '新密码至少 8 位'
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    localMessage.value = '两次输入的新密码不一致'
    return
  }
  const ok = await authStore.changePassword(oldPassword.value, newPassword.value, passwordVerifyType.value, passwordCode.value.trim())
  if (ok) {
    oldPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
    passwordCode.value = ''
  }
}

function switchAccount() {
  authStore.logout()
  router.replace('/login')
}
</script>

<template>
  <div class="settings-page">
    <header class="settings-header">
      <div>
        <h1>用户设置</h1>
        <p>{{ authStore.accountLabel }}</p>
      </div>
      <button class="ghost-btn" @click="router.push('/chat/new')">返回聊天</button>
    </header>

    <div class="settings-shell">
      <nav class="settings-nav" aria-label="设置分类">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          :class="['tab-btn', { active: activeTab === tab.id }]"
          @click="setTab(tab.id)"
        >
          <span>{{ tab.icon }}</span>
          <span>{{ tab.label }}</span>
        </button>
      </nav>

      <section class="settings-panel">
        <div v-if="activeTab === 'profile'" class="panel-content profile-panel">
          <div class="avatar-column">
            <div class="avatar-preview">
              <img v-if="avatarUrl" :src="avatarUrl" alt="头像" />
              <span v-else>{{ authStore.initials }}</span>
            </div>
            <input ref="uploadInput" type="file" accept="image/*" hidden @change="handleAvatarUpload" />
            <button class="ghost-btn" @click="pickAvatar">上传头像</button>
          </div>
          <div class="field-stack">
            <label>昵称</label>
            <input v-model="nickname" maxlength="30" placeholder="展示昵称" />
            <label>头像地址</label>
            <input v-model="avatarUrl" placeholder="上传后自动生成，也可以粘贴图片地址" />
            <button class="primary-btn" @click="saveProfile">保存资料</button>
          </div>
        </div>

        <div v-else-if="activeTab === 'account'" class="panel-content">
          <h2>绑定登录方式</h2>
          <div class="setting-row"><span>手机</span><strong>{{ authStore.currentUser?.phone || '未绑定' }} {{ authStore.currentUser?.phone_verified ? '已验证' : '' }}</strong></div>
          <div class="setting-row"><span>邮箱</span><strong>{{ authStore.currentUser?.email || '未绑定' }} {{ authStore.currentUser?.email_verified ? '已验证' : '' }}</strong></div>
          <div class="bind-box">
            <select v-model="bindTargetType">
              <option value="phone">绑定手机</option>
              <option value="email">绑定邮箱</option>
            </select>
            <input v-model="bindTarget" placeholder="手机号或邮箱" />
            <div class="inline-row two-actions">
              <input v-model="bindCode" placeholder="验证码" />
              <button class="ghost-btn" @click="sendBindCode">获取</button>
              <button class="primary-btn" @click="bindAccount">绑定</button>
            </div>
          </div>
        </div>

        <div v-else-if="activeTab === 'security'" class="panel-content">
          <h2>修改密码</h2>
          <div class="field-stack narrow">
            <input v-model="oldPassword" type="password" placeholder="当前密码" autocomplete="current-password" />
            <input v-model="newPassword" type="password" placeholder="新密码，至少 8 位" autocomplete="new-password" />
            <input v-model="confirmPassword" type="password" placeholder="确认新密码" autocomplete="new-password" />
            <div class="inline-row verify-row">
              <select v-model="passwordVerifyType">
                <option value="phone">手机验证</option>
                <option value="email">邮箱验证</option>
              </select>
              <input v-model="passwordCode" placeholder="验证码" />
              <button class="ghost-btn" @click="sendPasswordCode">获取</button>
            </div>
            <button class="primary-btn" @click="savePassword">验证并更新密码</button>
          </div>
        </div>

        <div v-else class="panel-content">
          <h2>账号与偏好</h2>
          <div class="setting-row"><span>登录账号</span><strong>{{ authStore.accountLabel }}</strong></div>
          <div class="setting-row"><span>建议功能</span><strong>旅行偏好、常用出发地、预算档位</strong></div>
          <div class="setting-row"><span>隐私</span><strong>后续可增加导出/清空数据</strong></div>
          <button class="danger-btn" @click="switchAccount">切换账号</button>
        </div>
      </section>
    </div>

    <p v-if="localMessage || authStore.profileMessage" class="save-message">{{ localMessage || authStore.profileMessage }}</p>
  </div>
</template>

<style scoped>
.settings-page { flex: 1; overflow-y: auto; padding: 24px; background: var(--bg-primary); }
.settings-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 18px; }
.settings-header h1 { font-size: 22px; color: var(--text-primary); }
.settings-header p { color: var(--text-secondary); font-size: 13px; margin-top: 4px; }
.settings-shell { display: grid; grid-template-columns: 190px minmax(0, 760px); gap: 16px; align-items: start; }
.settings-nav { display: flex; flex-direction: column; gap: 8px; }
.tab-btn { height: 42px; padding: 0 12px; border: 1px solid var(--border-color); background: var(--bg-secondary); color: var(--text-secondary); border-radius: 8px; cursor: pointer; display: flex; align-items: center; gap: 8px; text-align: left; }
.tab-btn.active { border-color: var(--accent-color); background: var(--accent-color-light); color: var(--text-primary); }
.settings-panel { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 8px; padding: 22px; min-height: 360px; }
.panel-content { max-width: 620px; animation: fadeIn 0.18s ease; }
.panel-content h2 { font-size: 17px; margin-bottom: 16px; color: var(--text-primary); }
.profile-panel { display: grid; grid-template-columns: 150px 1fr; gap: 24px; }
.avatar-column { display: flex; flex-direction: column; gap: 12px; align-items: center; }
.avatar-preview { width: 112px; height: 112px; border-radius: 50%; overflow: hidden; background: var(--accent-color-light); display: flex; align-items: center; justify-content: center; color: var(--accent-color); font-size: 34px; font-weight: 800; }
.avatar-preview img { width: 100%; height: 100%; object-fit: cover; }
.field-stack, .bind-box { display: flex; flex-direction: column; gap: 10px; }
.field-stack.narrow { max-width: 520px; }
.field-stack label { font-size: 12px; color: var(--text-secondary); }
input, select { padding: 10px 12px; border: 1px solid var(--border-color); border-radius: 8px; background: var(--bg-primary); color: var(--text-primary); min-width: 0; }
.primary-btn, .danger-btn, .ghost-btn { min-height: 36px; padding: 8px 13px; border-radius: 8px; cursor: pointer; }
.primary-btn { border: none; color: white; background: var(--accent-color); }
.ghost-btn { border: 1px solid var(--border-color); background: var(--bg-primary); color: var(--text-secondary); }
.ghost-btn:hover { color: var(--text-primary); border-color: var(--accent-color); }
.danger-btn { border: none; color: white; background: #ef4444; margin-top: 16px; }
.setting-row { display: flex; justify-content: space-between; gap: 12px; padding: 12px 0; border-bottom: 1px solid var(--border-color); color: var(--text-secondary); }
.setting-row strong { color: var(--text-primary); font-weight: 500; text-align: right; }
.inline-row { display: grid; gap: 8px; align-items: center; }
.inline-row.two-actions { grid-template-columns: 1fr auto auto; }
.inline-row.verify-row { grid-template-columns: 120px 1fr auto; }
.save-message { margin-top: 16px; color: var(--accent-color); }
@media (max-width: 840px) {
  .settings-shell { grid-template-columns: 1fr; }
  .settings-nav { flex-direction: row; overflow-x: auto; }
  .tab-btn { flex: 0 0 auto; }
  .profile-panel { grid-template-columns: 1fr; }
}
</style>