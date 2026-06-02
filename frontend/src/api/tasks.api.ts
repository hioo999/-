import { api } from './client'

export interface GenerationRecordData {
  recordId: number
  taskId: number
  projectId: number
  topicId: number
  platformContentId: number
  promptTemplateId: number
  promptTemplateVersionId: number
  promptSnapshot: Record<string, any>
  modelConfigId: number
  modelSnapshot: Record<string, any>
  params: Record<string, any>
  parsedOutput: Record<string, any>
  parseStatus: string
  rawResponseExcerpt?: string
  rawResponseText?: string
  createdAt: string | null
}

export interface UnifiedTaskListParams {
  projectId?: number
  topicId?: number
  platformContentId?: number
  taskType?: string
  status?: string
  limit?: number
}

export interface GenerationRecordListParams {
  taskId?: number
  projectId?: number
  topicId?: number
  platformContentId?: number
  parseStatus?: string
  includeRaw?: boolean
  limit?: number
}

export async function listUnifiedTasks(params: UnifiedTaskListParams = {}) {
  const res = await api.get('/api/tasks', { params })
  return res.data
}

export async function getUnifiedTask(taskId: number) {
  const res = await api.get(`/api/tasks/${taskId}`)
  return res.data
}

export async function retryUnifiedTask(taskId: number, params: { overrides?: Record<string, any> } = {}) {
  const res = await api.post(`/api/tasks/${taskId}/retry`, params)
  return res.data
}

export async function listGenerationRecords(params: GenerationRecordListParams = {}): Promise<{ code: number; data: { items: GenerationRecordData[]; total: number } }> {
  const res = await api.get('/api/generation-records', { params })
  return res.data
}
