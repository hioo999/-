import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { setAuthToken } from '../api/client'

export interface ActiveUser {
  name: string
  email: string
  token?: string
  isGuest?: boolean
  is_admin?: boolean
}

const STORAGE_KEY = 'ip-case-active-user'

function readStoredUser(): ActiveUser | undefined {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return undefined
    const user = JSON.parse(raw) as ActiveUser
    if (user.token) setAuthToken(user.token)
    return user
  } catch {
    return undefined
  }
}

export const useAuthStore = defineStore('auth', () => {
  const currentUser = ref<ActiveUser | undefined>(readStoredUser())
  const isGuestUser = computed(() => !currentUser.value?.token)
  const isAdminUser = computed(() => currentUser.value?.is_admin === true)

  function hydrate() {
    currentUser.value = readStoredUser()
  }

  function setCurrentUser(user: ActiveUser | undefined) {
    currentUser.value = user
    if (user?.token) {
      setAuthToken(user.token)
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(user))
    } else {
      setAuthToken('')
      window.localStorage.removeItem(STORAGE_KEY)
    }
  }

  function logout() {
    setCurrentUser(undefined)
  }

  return {
    currentUser,
    isGuestUser,
    isAdminUser,
    hydrate,
    setCurrentUser,
    logout,
  }
})
