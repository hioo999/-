import { api } from './client'

export interface ContentColumnData {
  id?: number
  name: string
  persona_id?: number
  goal?: string
  target_platform?: string
  duration?: string
  structure?: string
  opening_style?: string
  cta?: string
  default_template?: string
  default_voice?: string
  default_bgm?: string
  notes?: string
  sort_order?: number
  is_active?: boolean
}

export async function listColumns(personaId = 0) {
  const res = await api.get('/api/copilot/columns', { params: { persona_id: personaId } })
  return res.data
}

export async function createColumn(data: ContentColumnData) {
  const res = await api.post('/api/copilot/columns', data)
  return res.data
}

export async function updateColumn(id: number, data: ContentColumnData) {
  const res = await api.put(`/api/copilot/columns/${id}`, data)
  return res.data
}

export async function deleteColumn(id: number) {
  const res = await api.delete(`/api/copilot/columns/${id}`)
  return res.data
}

export async function generateTopicPlan(params: {
  extracted_content: string
  persona_id?: number
  column_id?: number
  count?: number
  extra_requirements?: string
}) {
  const res = await api.post('/api/copilot/strategy/topics', params)
  return res.data
}

export async function optimizeHooks(params: {
  script_content: string
  persona_id?: number
  column_id?: number
  count?: number
}) {
  const res = await api.post('/api/copilot/strategy/hooks', params)
  return res.data
}

export async function generatePublishPackage(params: {
  script_content: string
  cover_prompt?: string
  target_platform?: string
  persona_id?: number
  column_id?: number
}) {
  const res = await api.post('/api/copilot/strategy/publish-package', params)
  return res.data
}

export async function qualityCheck(params: {
  script_content: string
  cover_prompt?: string
  publish_copy?: string
  persona_id?: number
  column_id?: number
}) {
  const res = await api.post('/api/copilot/strategy/quality-check', params)
  return res.data
}
