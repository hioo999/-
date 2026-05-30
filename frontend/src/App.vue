<script setup lang="ts">
import { ref, onMounted } from 'vue'
import CopilotWorkspace from './views/CopilotWorkspace.vue'
import { setAuthToken } from './api'

interface ActiveUser {
  name: string
  email: string
  token?: string
  isGuest?: boolean
  is_admin?: boolean
}

const STORAGE_KEY = 'ip-case-active-user'
const currentUser = ref<ActiveUser | undefined>()

onMounted(() => {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return
    const user = JSON.parse(raw) as ActiveUser
    currentUser.value = user
    if (user.token) setAuthToken(user.token)
  } catch {
    currentUser.value = undefined
  }
})

function handleLogout() {
  currentUser.value = undefined
  setAuthToken('')
  window.localStorage.removeItem(STORAGE_KEY)
  window.location.hash = ''
}
</script>

<template>
  <CopilotWorkspace :current-user="currentUser" @logout="handleLogout" />
</template>
