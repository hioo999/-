import { api } from './client'

export interface TeleprompterCloudSettings {
  fontSize: string
  lineHeight: string
  scrollSpeed: number
  theme: string
  mirrorMode: boolean
  countdownEnabled: boolean
  countdownSeconds: number
}

export interface TeleprompterDraftPayload {
  title: string
  content: string
  settings: TeleprompterCloudSettings
  currentParagraphIndex: number
  currentScrollPosition: number
  source: string
  sourceId: string
  status: string
}

export interface TeleprompterDraftSummary {
  draftId: number
  title: string
  source: string
  sourceId: string
  wordCount: number
  paragraphCount: number
  status: string
  currentParagraphIndex: number
  currentScrollPosition: number
  updatedAt: string | null
  createdAt: string | null
}

export interface TeleprompterDraft extends TeleprompterDraftSummary {
  content: string
  settings: TeleprompterCloudSettings
}

export interface TeleprompterAnalyticsEventPayload {
  eventName: string
  eventTime?: string
  sessionId?: string
  properties?: Record<string, unknown>
}

export async function getRecentTeleprompterDraft(): Promise<{ code: number; data: TeleprompterDraftSummary | null }> {
  const res = await api.get('/api/teleprompter/drafts/recent')
  return res.data
}

export async function listTeleprompterDrafts(params: { page?: number; pageSize?: number } = {}): Promise<{ code: number; data: { items: TeleprompterDraftSummary[]; page: number; pageSize: number; total: number } }> {
  const res = await api.get('/api/teleprompter/drafts', { params })
  return res.data
}

export async function getTeleprompterDraft(draftId: number): Promise<{ code: number; data: TeleprompterDraft }> {
  const res = await api.get(`/api/teleprompter/drafts/${draftId}`)
  return res.data
}

export async function createTeleprompterDraft(params: TeleprompterDraftPayload): Promise<{ code: number; data: TeleprompterDraftSummary; message: string }> {
  const res = await api.post('/api/teleprompter/drafts', params)
  return res.data
}

export async function updateTeleprompterDraft(draftId: number, params: TeleprompterDraftPayload): Promise<{ code: number; data: TeleprompterDraftSummary; message: string }> {
  const res = await api.put(`/api/teleprompter/drafts/${draftId}`, params)
  return res.data
}

export async function deleteTeleprompterDraft(draftId: number): Promise<{ code: number; data: { draftId: number; deleted: boolean }; message: string }> {
  const res = await api.delete(`/api/teleprompter/drafts/${draftId}`)
  return res.data
}

export async function getTeleprompterScript(scriptId: number) {
  const res = await api.get(`/api/teleprompter/scripts/${scriptId}`)
  return res.data
}

export async function getTeleprompterVideoPackageScript(packageId: number) {
  const res = await api.get(`/api/teleprompter/video-packages/${packageId}/teleprompter-script`)
  return res.data
}

export async function reportTeleprompterEvent(params: TeleprompterAnalyticsEventPayload) {
  const res = await api.post('/api/teleprompter/analytics/events', params)
  return res.data
}
