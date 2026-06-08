<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ProductionCenter from '../components/ProductionCenter.vue'
import WorkspaceLayout from '../layouts/WorkspaceLayout.vue'
import type { ActiveUser } from '../stores/auth'

defineProps<{
  currentUser?: ActiveUser
}>()

const emit = defineEmits<{
  logout: []
}>()

const route = useRoute()
const router = useRouter()

const initialTab = computed(() => {
  const tab = String(route.query.tab || '')
  if (['overview', 'wechat', 'platform', 'teleprompter', 'advanced'].includes(tab)) {
    return tab as 'overview' | 'wechat' | 'platform' | 'teleprompter' | 'advanced'
  }
  return undefined
})

watch(
  () => route.query.tab,
  (tab) => {
    if (route.path === '/workspace/platform' && !tab) {
      router.replace({ path: '/workspace/content', query: { tab: 'platform' } })
    }
  },
  { immediate: true },
)
</script>

<template>
  <WorkspaceLayout :current-user="currentUser" @logout="emit('logout')">
    <ProductionCenter
      :initial-tab="initialTab"
      :current-user="currentUser"
    />
  </WorkspaceLayout>
</template>
