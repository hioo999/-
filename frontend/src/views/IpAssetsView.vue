<script setup lang="ts">
import Sprint1CaseWorkspace from './Sprint1CaseWorkspace.vue'
import WorkspaceLayout from '../layouts/WorkspaceLayout.vue'
import type { ActiveUser } from '../stores/auth'

defineProps<{
  currentUser?: ActiveUser
}>()

const emit = defineEmits<{
  logout: []
  requestLogin: [path?: string | null]
}>()
</script>

<template>
  <WorkspaceLayout
    :current-user="currentUser"
    @logout="emit('logout')"
    @request-login="emit('requestLogin', $event)"
  >
    <Sprint1CaseWorkspace :current-user="currentUser" @request-login="emit('requestLogin', $event)" />
  </WorkspaceLayout>
</template>
