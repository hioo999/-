<script setup lang="ts">
import { ref, watchEffect } from 'vue'
import ReversalDramaPanel from '../components/ReversalDramaPanel.vue'
import WorkspaceLayout from '../layouts/WorkspaceLayout.vue'
import type { ActiveUser } from '../stores/auth'

defineProps<{
  currentUser?: ActiveUser
}>()

const emit = defineEmits<{
  logout: []
}>()

const workspaceRef = ref<{
  generateDrama?: () => void
  isGeneratingDrama?: boolean
  dramaGenerateReason?: string
} | null>(null)
const isGeneratingDrama = ref(false)
const dramaGenerateReason = ref('')

watchEffect(() => {
  const ws = workspaceRef.value
  if (!ws) return
  isGeneratingDrama.value = Boolean(ws.isGeneratingDrama)
  dramaGenerateReason.value = String(ws.dramaGenerateReason || '')
})

function handleGenerateDrama() {
  workspaceRef.value?.generateDrama?.()
}
</script>

<template>
  <WorkspaceLayout
    :current-user="currentUser"
    :is-generating-drama="isGeneratingDrama"
    :drama-generate-reason="dramaGenerateReason"
    @logout="emit('logout')"
    @generate-drama="handleGenerateDrama"
  >
    <ReversalDramaPanel
      ref="workspaceRef"
      :current-user="currentUser"
      @logout="emit('logout')"
    />
  </WorkspaceLayout>
</template>
