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
  } catch (error) {
    dashboardError.value = error instanceof Error ? error.message : '首页数据加载失败'
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
      <section v-if="dashboardError" class="dashboard-error" role="status">
        <div>
          <strong>首页数据暂时不可用</strong>
          <span>{{ dashboardError }}</span>
        </div>
        <button class="btn btn-ghost btn-sm" :disabled="dashboardLoading" @click="loadDashboard">重试</button>
      </section>
      <HomeToolCards
        :dashboard="dashboard"
        :loading="dashboardLoading"
        :error="dashboardError"
        @select="selectWorkspaceMode"
      />
    </template>
  </AppLayout>
</template>

<style scoped>
.dashboard-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
  padding: 14px 16px;
  border: 1px solid rgba(217, 119, 6, 0.22);
  border-radius: 18px;
  background: rgba(217, 119, 6, 0.08);
  color: #92400e;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.05);
}

.dashboard-error div {
  display: grid;
  gap: 4px;
}

.dashboard-error strong {
  font-size: 14px;
}

.dashboard-error span {
  font-size: 13px;
  line-height: 1.5;
}
</style>
