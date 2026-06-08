<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { loginAccount, registerAccount } from '../api/auth'
import type { ActiveUser } from '../stores/auth'

const props = defineProps<{
  open: boolean
  redirectHint?: string | null
}>()

const emit = defineEmits<{
  close: []
  success: [user: ActiveUser]
}>()

type AuthMode = 'login' | 'register'

const mode = ref<AuthMode>('login')
const isSubmitting = ref(false)
const errorMessage = ref('')

const form = reactive({
  name: '',
  email: '',
  password: '',
})

watch(
  () => props.open,
  (open) => {
    if (!open) return
    errorMessage.value = ''
    mode.value = 'login'
  },
)

function resetPasswordField() {
  form.password = ''
}

function switchMode(nextMode: AuthMode) {
  mode.value = nextMode
  errorMessage.value = ''
  resetPasswordField()
}

async function handleSubmit() {
  errorMessage.value = ''
  const email = form.email.trim()
  const password = form.password.trim()
  if (!email || !password) {
    errorMessage.value = '请填写邮箱和密码。'
    return
  }
  if (mode.value === 'register' && !form.name.trim()) {
    errorMessage.value = '请填写昵称。'
    return
  }

  isSubmitting.value = true
  try {
    const res = mode.value === 'register'
      ? await registerAccount({ name: form.name.trim(), email, password })
      : await loginAccount({ email, password })

    emit('success', {
      name: res.data.user.name,
      email: res.data.user.email,
      token: res.data.token,
      isGuest: false,
      is_admin: res.data.user.is_admin === true,
    })
  } catch (err: any) {
    const detail = err?.response?.data?.detail
    errorMessage.value = typeof detail === 'string'
      ? detail
      : detail?.message || err?.message || '登录失败，请稍后重试。'
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div v-if="open" class="auth-backdrop" role="presentation" @click.self="emit('close')">
    <section class="auth-panel" role="dialog" aria-modal="true" aria-labelledby="auth-panel-title">
      <button class="auth-close" type="button" aria-label="关闭" @click="emit('close')">×</button>
      <div class="auth-copy">
        <span class="auth-eyebrow">账号登录</span>
        <h2 id="auth-panel-title">{{ mode === 'login' ? '登录后解锁全部功能' : '注册新账号' }}</h2>
        <p>
          登录后可新建 IP 档案、使用生产中心、保存云端历史。
          <span v-if="redirectHint">即将前往：{{ redirectHint }}</span>
        </p>
      </div>

      <div class="auth-tabs" role="tablist" aria-label="登录方式">
        <button
          type="button"
          role="tab"
          :aria-selected="mode === 'login'"
          :class="{ active: mode === 'login' }"
          @click="switchMode('login')"
        >登录</button>
        <button
          type="button"
          role="tab"
          :aria-selected="mode === 'register'"
          :class="{ active: mode === 'register' }"
          @click="switchMode('register')"
        >注册</button>
      </div>

      <form class="auth-form" @submit.prevent="handleSubmit">
        <label v-if="mode === 'register'">
          昵称
          <input v-model="form.name" class="input" autocomplete="name" placeholder="例如：小美内容官" />
        </label>
        <label>
          邮箱
          <input v-model="form.email" class="input" type="email" autocomplete="username" placeholder="you@example.com" />
        </label>
        <label>
          密码
          <input v-model="form.password" class="input" type="password" autocomplete="current-password" placeholder="至少 6 位" />
        </label>
        <p v-if="errorMessage" class="auth-error" role="alert">{{ errorMessage }}</p>
        <button class="btn btn-primary btn-lg auth-submit" type="submit" :disabled="isSubmitting">
          {{ isSubmitting ? '提交中...' : (mode === 'login' ? '登录并继续' : '注册并继续') }}
        </button>
      </form>

      <p class="auth-footnote">
        暂不登录？可先使用
        <button type="button" class="inline-link" @click="emit('close')">提词器试用</button>
      </p>
    </section>
  </div>
</template>

<style scoped>
.auth-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1100;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(15, 23, 42, 0.48);
  backdrop-filter: blur(8px);
}

.auth-panel {
  position: relative;
  display: grid;
  gap: 18px;
  width: min(440px, 100%);
  padding: 24px;
  border: 1px solid rgba(255, 255, 255, 0.72);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: var(--shadow-lg);
}

.auth-close {
  position: absolute;
  top: 14px;
  right: 14px;
  width: 36px;
  height: 36px;
  border: 0;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.06);
  color: var(--color-text-secondary);
  cursor: pointer;
  font-size: 22px;
  line-height: 1;
}

.auth-copy {
  display: grid;
  gap: 8px;
  padding-right: 28px;
}

.auth-eyebrow {
  color: var(--color-text-accent);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.auth-copy h2 {
  margin: 0;
  color: var(--color-text-primary);
  font-size: 24px;
  font-weight: 800;
  letter-spacing: -0.04em;
}

.auth-copy p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: 14px;
  line-height: 1.7;
}

.auth-tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  padding: 4px;
  border: 1px solid var(--color-border);
  border-radius: 999px;
  background: var(--color-bg-tertiary);
}

.auth-tabs button {
  min-height: 40px;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  font: inherit;
  font-size: 13px;
  font-weight: 700;
}

.auth-tabs button.active {
  background: #fff;
  color: var(--color-accent-primary);
  box-shadow: var(--shadow-sm);
}

.auth-form {
  display: grid;
  gap: 12px;
}

.auth-form label {
  display: grid;
  gap: 8px;
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 700;
}

.auth-error {
  margin: 0;
  padding: 10px 12px;
  border-radius: 14px;
  background: rgba(220, 38, 38, 0.08);
  color: var(--color-error);
  font-size: 13px;
  font-weight: 700;
}

.auth-submit {
  width: 100%;
}

.auth-footnote {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 13px;
  text-align: center;
}

.inline-link {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--color-accent-primary);
  cursor: pointer;
  font: inherit;
  font-weight: 700;
}
</style>
