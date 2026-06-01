import { api } from './client'
import type { ToolKey } from '../components/HomeToolCards.vue'

export interface DashboardOverview {
  ipCompleteness: {
    value: number
    missingItems: string[]
  }
  taskSummary: {
    total: number
    running: number
    failed: number
    pendingPublish: number
  }
  assetSummary: {
    total: number
    scripts: number
    images: number
    publishPackages: number
  }
  modelStatus: {
    textReady: boolean
    imageReady: boolean
    videoReady: boolean
  }
  todayActions: Array<{
    title: string
    status: string
    owner: string
    action: string
    actionKey: ToolKey
  }>
  recentContents: unknown[]
  recentTasks: unknown[]
  lastActivityAt: string | null
}

export async function getDashboardOverview() {
  const res = await api.get<{ code: number; data: DashboardOverview; message?: string }>('/api/dashboard/overview')
  return res.data
}
