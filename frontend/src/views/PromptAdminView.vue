<script setup lang="ts">
import PromptAdminPanel from '../components/PromptAdminPanel.vue'
import WorkspaceLayout from '../layouts/WorkspaceLayout.vue'
import type { ActiveUser } from '../stores/auth'

defineOptions({ inheritAttrs: false })

defineProps<{
  currentUser?: ActiveUser
}>()

defineEmits<{
  logout: []
}>()
</script>

<template>
  <WorkspaceLayout :current-user="currentUser" @logout="$emit('logout')">
    <PromptAdminPanel :current-user="currentUser" />
  </WorkspaceLayout>
</template>
