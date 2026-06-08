<script setup lang="ts">
/** @deprecated 请使用 WorkspaceLayout */
import WorkspaceLayout from './WorkspaceLayout.vue'
import type { ActiveUser } from '../stores/auth'

defineProps<{
  currentUser?: ActiveUser
}>()

const emit = defineEmits<{
  logout: []
}>()
</script>

<template>
  <WorkspaceLayout :current-user="currentUser" @logout="emit('logout')">
    <slot />
  </WorkspaceLayout>
</template>
