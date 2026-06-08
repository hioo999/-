<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { RouterView, useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import AuthPanel from './components/AuthPanel.vue'
import { useGuestAccess } from './composables/useGuestAccess'
import { useAuthStore } from './stores/auth'

const authStore = useAuthStore()
const { currentUser } = storeToRefs(authStore)
const router = useRouter()
const route = useRoute()
const { authPanelOpen, pendingRedirect, promptLogin, closeAuthPanel, consumeRedirect } = useGuestAccess()

const redirectHint = computed(() => {
  const path = pendingRedirect.value || String(route.query.redirect || '')
  if (!path) return null
  if (path.startsWith('/workspace/ip-assets')) return 'IP 档案'
  if (path.startsWith('/workspace/content')) return '生产中心'
  if (path.startsWith('/settings')) return '系统设置'
  return '目标页面'
})

onMounted(authStore.hydrate)

watch(
  () => route.query.login,
  (value) => {
    if (value && authStore.isGuestUser) {
      promptLogin(typeof route.query.redirect === 'string' ? route.query.redirect : null)
    }
  },
  { immediate: true },
)

function handleLogout() {
  authStore.logout()
  router.push('/')
}

function handleAuthSuccess(user: Parameters<typeof authStore.setCurrentUser>[0]) {
  authStore.setCurrentUser(user)
  closeAuthPanel()
  const redirect = consumeRedirect() || (typeof route.query.redirect === 'string' ? route.query.redirect : null)
  if (redirect) {
    const targetPath = redirect.split('?')[0]
    if (route.path !== targetPath) {
      router.replace(redirect)
    } else if (route.query.login) {
      router.replace({ path: targetPath })
    }
    return
  }
  if (route.query.login) {
    router.replace('/')
  }
}
</script>

<template>
  <RouterView v-slot="{ Component, route: activeRoute }">
    <component
      :is="Component"
      :current-user="currentUser"
      :initial-mode="activeRoute.meta.initialMode"
      @logout="handleLogout"
      @request-login="promptLogin"
    />
  </RouterView>

  <AuthPanel
    :open="authPanelOpen"
    :redirect-hint="redirectHint"
    @close="closeAuthPanel"
    @success="handleAuthSuccess"
  />
</template>
