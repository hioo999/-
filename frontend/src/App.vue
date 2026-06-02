<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterView, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAuthStore } from './stores/auth'

const authStore = useAuthStore()
const { currentUser } = storeToRefs(authStore)
const router = useRouter()

onMounted(authStore.hydrate)

function handleLogout() {
  authStore.logout()
  router.push('/')
}
</script>

<template>
  <RouterView v-slot="{ Component, route }">
    <component
      :is="Component"
      :current-user="currentUser"
      :initial-mode="route.meta.initialMode"
      @logout="handleLogout"
    />
  </RouterView>
</template>
