<script setup lang="ts">
import ModelSettingsPanel from '../components/ModelSettingsPanel.vue'
import WorkspaceLayout from '../layouts/WorkspaceLayout.vue'
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
    <ModelSettingsPanel :current-user="currentUser" />
  </WorkspaceLayout>
</template>
