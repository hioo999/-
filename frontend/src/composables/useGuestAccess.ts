import { ref } from 'vue'

const authPanelOpen = ref(false)
const pendingRedirect = ref<string | null>(null)

export function isGuestAllowedPath(path: string) {
  const base = path.split('?')[0]
  if (base === '/') return true
  if (base.startsWith('/publish')) return true
  if (base === '/tools/teleprompter') return true
  return false
}

export function useGuestAccess() {
  function promptLogin(redirectPath?: string | null) {
    pendingRedirect.value = redirectPath || null
    authPanelOpen.value = true
  }

  function closeAuthPanel() {
    authPanelOpen.value = false
  }

  function consumeRedirect() {
    const path = pendingRedirect.value
    pendingRedirect.value = null
    return path
  }

  return {
    authPanelOpen,
    pendingRedirect,
    promptLogin,
    closeAuthPanel,
    consumeRedirect,
    isGuestAllowedPath,
  }
}
