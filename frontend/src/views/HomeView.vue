<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import HomeToolCards, { type ToolKey } from '../components/HomeToolCards.vue'
import AppLayout from '../layouts/AppLayout.vue'
import { getDashboardOverview, type DashboardOverview } from '../api/dashboard.api'
import { modePathMap } from '../stores/workspace'
import type { ActiveUser } from '../stores/auth'

const props = defineProps<{
  currentUser?: ActiveUser
}>()

const emit = defineEmits<{
  logout: []
}>()

const router = useRouter()
const dashboard = ref<DashboardOverview | null>(null)
const dashboardLoading = ref(false)
const dashboardError = ref('')

async function loadDashboard() {
  if (!props.currentUser?.token) return
  dashboardLoading.value = true
  dashboardError.value = ''
  try {
    const res = await getDashboardOverview()
    dashboard.value = res.data
  } catch {
    dashboardError.value = '实时数据暂未同步，当前展示产品导览内容。'
  } finally {
    dashboardLoading.value = false
  }
}

function selectWorkspaceMode(mode: ToolKey) {
  router.push(modePathMap[mode])
}

onMounted(loadDashboard)
</script>

<template>
  <AppLayout :current-user="currentUser" @logout="emit('logout')">
    <template #default>
      <HomeToolCards
        :dashboard="dashboard"
        :loading="dashboardLoading"
        :error="dashboardError"
        @select="selectWorkspaceMode"
      />
    </template>
  </AppLayout>
</template>
