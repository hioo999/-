<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import WorkspaceHeader from '../components/WorkspaceHeader.vue'
import { isGuestAllowedPath, useGuestAccess } from '../composables/useGuestAccess'
import type { ActiveUser } from '../stores/auth'

const props = defineProps<{
  currentUser?: ActiveUser
  isGeneratingDrama?: boolean
  dramaGenerateReason?: string
}>()

const emit = defineEmits<{
  logout: []
  generateDrama: []
  requestLogin: [path?: string | null]
}>()

const router = useRouter()
const route = useRoute()
const { promptLogin } = useGuestAccess()

const currentPath = computed(() => route.path)
const isGuestUser = computed(() => !props.currentUser?.token)
const isAdminUser = computed(() => props.currentUser?.is_admin === true)

function navigate(path: string) {
  if (isGuestUser.value && !isGuestAllowedPath(path)) {
    promptLogin(path)
    emit('requestLogin', path)
    return
  }
  if ((path === '/settings/models' || path === '/admin/prompts') && !isAdminUser.value) {
    router.push('/')
    return
  }
  router.push(path)
}

function openLogin() {
  promptLogin(route.fullPath === '/' ? null : route.fullPath)
  emit('requestLogin', route.fullPath === '/' ? null : route.fullPath)
}
</script>

<template>
  <div class="workspace-shell">
    <WorkspaceHeader
      :current-path="currentPath"
      :current-user="currentUser"
      :is-guest-user="isGuestUser"
      :is-admin-user="isAdminUser"
      :is-generating-drama="isGeneratingDrama"
      :drama-generate-reason="dramaGenerateReason"
      @navigate="navigate"
      @logout="emit('logout')"
      @generate-drama="emit('generateDrama')"
      @request-login="openLogin"
    />
    <main class="workspace-shell-main">
      <slot />
    </main>
  </div>
</template>

<style scoped>
.workspace-shell {
  position: relative;
  z-index: 1;
  min-height: 100vh;
  background: var(--color-bg-primary);
}

.workspace-shell-main {
  min-height: calc(100vh - 64px);
  padding: 28px 32px 44px;
}

@media (max-width: 720px) {
  .workspace-shell-main {
    padding: 14px;
  }
}
</style>
