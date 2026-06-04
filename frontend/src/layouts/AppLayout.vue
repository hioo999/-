<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import WorkspaceHeader from '../components/WorkspaceHeader.vue'
import { modeFromPath, modePathMap, type WorkspaceMode } from '../stores/workspace'
import type { ActiveUser } from '../stores/auth'

const props = defineProps<{
  currentUser?: ActiveUser
}>()

const emit = defineEmits<{
  logout: []
}>()

const router = useRouter()
const workspaceMode = computed(() => modeFromPath(router.currentRoute.value.path))
const isGuestUser = computed(() => props.currentUser?.isGuest === true && !props.currentUser?.token)
const isAdminUser = computed(() => props.currentUser?.is_admin === true)

function selectWorkspaceMode(mode: WorkspaceMode) {
  if (isGuestUser.value && mode !== 'teleprompter') {
    router.push(modePathMap.teleprompter)
    return
  }
  if ((mode === 'models' || mode === 'prompts') && !isAdminUser.value) {
    router.push(modePathMap.home)
    return
  }
  router.push(modePathMap[mode])
}

watch([workspaceMode, isAdminUser], ([mode, admin]) => {
  if ((mode === 'models' || mode === 'prompts') && !admin) {
    router.replace(modePathMap.home)
  }
}, { immediate: true })
</script>

<template>
  <div class="app-shell" :class="{ 'workspace-home': workspaceMode === 'home', 'workspace-ip': workspaceMode === 'ip' }">
    <WorkspaceHeader
      :workspace-mode="workspaceMode"
      :current-user="currentUser"
      :is-guest-user="isGuestUser"
      :is-admin-user="isAdminUser"
      :is-generating-drama="false"
      drama-generate-reason=""
      @select="selectWorkspaceMode"
      @logout="emit('logout')"
      @generate-drama="selectWorkspaceMode('reversal')"
    />
    <p class="sr-only" role="status" aria-live="polite"></p>
    <main class="app-shell-main">
      <slot :select-workspace-mode="selectWorkspaceMode" />
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  position: relative;
  z-index: 1;
  min-height: 100vh;
  background: var(--color-bg-primary);
}

.app-shell-main {
  min-height: calc(100vh - 64px);
  padding: 28px 32px 44px;
}

.workspace-home .app-shell-main {
  padding: 28px 32px 48px;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@media (max-width: 720px) {
  .app-shell-main,
  .workspace-home .app-shell-main {
    padding: 14px;
  }
}
</style>
