<script setup lang="ts">
import { useRouter } from 'vue-router'
import HomeToolCards, { type ToolKey } from '../components/HomeToolCards.vue'
import AppLayout from '../layouts/AppLayout.vue'
import { modePathMap } from '../stores/workspace'
import type { ActiveUser } from '../stores/auth'

defineProps<{
  currentUser?: ActiveUser
}>()

const emit = defineEmits<{
  logout: []
}>()

const router = useRouter()

function selectWorkspaceMode(mode: ToolKey) {
  router.push(modePathMap[mode])
}
</script>

<template>
  <AppLayout :current-user="currentUser" @logout="emit('logout')">
    <template #default>
      <HomeToolCards
        @select="selectWorkspaceMode"
      />
    </template>
  </AppLayout>
</template>
