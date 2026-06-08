import { api } from './client'

export interface TeleprompterCloudSettings {
  fontSize: string
  lineHeight: string
  scrollSpeed: number
  theme: string
  mirrorMode: boolean
  countdownEnabled: boolean
  countdownSeconds: number
  readingWidthMode?: string
  eyeContactMode?: string
  cameraFocusPosition?: string
  recordingMode?: string
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

export interface TeleprompterQueuePayload {
  activeScriptId: string
  scripts: Array<Record<string, unknown>>
  settings: Record<string, unknown>
}

export interface TeleprompterQueue extends TeleprompterQueuePayload {
  queueId: number
  updatedAt: string | null
  createdAt: string | null
}

export interface LiveTeleprompterHost {
  name: string
  role: string
}

export interface LiveTeleprompterProduct {
  name: string
  category: string
  positioning: string
  originalPrice: string
  livePrice: string
  offer: string
  sellingPoints: string[]
  painPoints: string[]
  suitableUsers: string
  faq: string[]
  notes: string
  durationMinutes: number
}

export interface LiveTeleprompterGeneratePayload {
  title: string
  platform: string
  liveStart: string
  liveDurationMinutes: number
  gmvTarget: string
  audience: string
  style: string
  hostCount: number
  hosts: LiveTeleprompterHost[]
  benefits: string
  extraRequirements: string
  complianceMode: boolean
  templateKey: string
  themeKey: string
  aiEnhance: boolean
  saveHistory: boolean
  products: LiveTeleprompterProduct[]
}

export interface LiveTeleprompterSection {
  sectionId: string
  title: string
  timeRange: string
  goal: string
  plainText: string
}

export interface LiveTeleprompterGenerateResult {
  scriptId: number | null
  title: string
  templateKey: string
  themeKey: string
  plainText: string
  html: string
  sections: LiveTeleprompterSection[]
  mustRemember: string[]
  complianceTips: string[]
  generatedBy: string
}

export interface LiveTeleprompterTemplate {
  templateId?: number
  key: string
  name: string
  description: string
  defaultStyle: string
  openingFocus: string
  productFocus: string
  complianceTips: string[]
  sectionBlueprint?: string[]
  isCustom?: boolean
  isActive?: boolean
}

export interface LiveTeleprompterTheme {
  key: string
  name: string
  accent: string
  bg1: string
  bg2: string
  card: string
  text: string
}

export interface LiveTeleprompterHistorySummary {
  scriptId: number
  title: string
  templateKey: string
  wordCount: number
  sectionCount: number
  status: string
  createdAt: string | null
  updatedAt: string | null
}

export interface LiveTeleprompterHistoryDetail extends LiveTeleprompterHistorySummary {
  request: Record<string, unknown>
  result: LiveTeleprompterGenerateResult | Record<string, unknown>
  plainText: string
  html: string
}

export interface LiveTeleprompterHistoryPayload {
  title: string
  templateKey: string
  request: Record<string, unknown>
  result: Record<string, unknown>
  plainText: string
  html: string
}

export interface LiveTeleprompterPreflightFinding {
  severity: 'success' | 'warning' | 'error'
  label: string
  suggestion: string
}

export interface LiveTeleprompterReviewPayload {
  scriptId?: number | null
  title: string
  actualGmv: string
  productResults: Array<Record<string, unknown>>
  winningLines: string
  weakProducts: string
  audienceQuestions: string
  notes: string
}

export async function getTeleprompterQueue(): Promise<{ code: number; data: TeleprompterQueue | null }> {
  const res = await api.get('/api/teleprompter/queue')
  return res.data
}

export async function saveTeleprompterQueue(params: TeleprompterQueuePayload): Promise<{ code: number; data: TeleprompterQueue; message: string }> {
  const res = await api.put('/api/teleprompter/queue', params)
  return res.data
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

export async function generateLiveTeleprompterScript(params: LiveTeleprompterGeneratePayload): Promise<{ code: number; data: LiveTeleprompterGenerateResult; message: string }> {
  const res = await api.post('/api/teleprompter/live-script/generate', params)
  return res.data
}

export async function listLiveTeleprompterTemplates(): Promise<{ code: number; data: { items: LiveTeleprompterTemplate[] } }> {
  const res = await api.get('/api/teleprompter/live-script/templates')
  return res.data
}

export async function listLiveTeleprompterThemes(): Promise<{ code: number; data: { items: LiveTeleprompterTheme[] } }> {
  const res = await api.get('/api/teleprompter/live-script/themes')
  return res.data
}

export async function importLiveTeleprompterProducts(params: { rawText: string }): Promise<{ code: number; data: { items: LiveTeleprompterProduct[]; count: number }; message: string }> {
  const res = await api.post('/api/teleprompter/live-script/import-products', params)
  return res.data
}

export async function preflightLiveTeleprompterScript(params: { request: LiveTeleprompterGeneratePayload }): Promise<{ code: number; data: { items: LiveTeleprompterPreflightFinding[]; passed: boolean } }> {
  const res = await api.post('/api/teleprompter/live-script/preflight', params)
  return res.data
}

export async function reviewLiveTeleprompterScript(params: LiveTeleprompterReviewPayload): Promise<{ code: number; data: { markdown: string; suggestions: string[]; productLines: string[] }; message: string }> {
  const res = await api.post('/api/teleprompter/live-script/review', params)
  return res.data
}

export async function createLiveTeleprompterTemplate(params: LiveTeleprompterTemplate): Promise<{ code: number; data: LiveTeleprompterTemplate; message: string }> {
  const res = await api.post('/api/teleprompter/live-script/templates', params)
  return res.data
}

export async function updateLiveTeleprompterTemplate(templateId: number, params: LiveTeleprompterTemplate): Promise<{ code: number; data: LiveTeleprompterTemplate; message: string }> {
  const res = await api.put(`/api/teleprompter/live-script/templates/${templateId}`, params)
  return res.data
}

export async function deleteLiveTeleprompterTemplate(templateId: number): Promise<{ code: number; data: { templateId: number; deleted: boolean }; message: string }> {
  const res = await api.delete(`/api/teleprompter/live-script/templates/${templateId}`)
  return res.data
}

export async function listLiveTeleprompterHistory(params: { page?: number; pageSize?: number } = {}): Promise<{ code: number; data: { items: LiveTeleprompterHistorySummary[]; page: number; pageSize: number; total: number } }> {
  const res = await api.get('/api/teleprompter/live-script/history', { params })
  return res.data
}

export async function getLiveTeleprompterHistory(scriptId: number): Promise<{ code: number; data: LiveTeleprompterHistoryDetail }> {
  const res = await api.get(`/api/teleprompter/live-script/history/${scriptId}`)
  return res.data
}

export async function saveLiveTeleprompterHistory(params: LiveTeleprompterHistoryPayload): Promise<{ code: number; data: LiveTeleprompterHistorySummary; message: string }> {
  const res = await api.post('/api/teleprompter/live-script/history', params)
  return res.data
}

export async function deleteLiveTeleprompterHistory(scriptId: number): Promise<{ code: number; data: { scriptId: number; deleted: boolean }; message: string }> {
  const res = await api.delete(`/api/teleprompter/live-script/history/${scriptId}`)
  return res.data
}
