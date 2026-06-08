<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import HomeDashboard from '../components/HomeDashboard.vue'
import WorkspaceLayout from '../layouts/WorkspaceLayout.vue'
import { isGuestAllowedPath, useGuestAccess } from '../composables/useGuestAccess'
import type { ActiveUser } from '../stores/auth'

const props = defineProps<{
  currentUser?: ActiveUser
}>()

const emit = defineEmits<{
  logout: []
  requestLogin: [path?: string | null]
}>()

const router = useRouter()
const { promptLogin } = useGuestAccess()

const isGuestUser = computed(() => !props.currentUser?.token)

function navigate(path: string) {
  if (isGuestUser.value && !isGuestAllowedPath(path)) {
    promptLogin(path)
    emit('requestLogin', path)
    return
  }
  router.push(path)
}
</script>

<template>
  <WorkspaceLayout :current-user="currentUser" @logout="emit('logout')" @request-login="emit('requestLogin', $event)">
    <HomeDashboard :is-guest-user="isGuestUser" @navigate="navigate" @request-login="emit('requestLogin', $event)" />
  </WorkspaceLayout>
</template>
