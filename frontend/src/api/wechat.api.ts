import { api } from './client'

export interface WechatAccountPayload {
  name: string
  appId: string
  appSecret?: string
  originalId?: string
  feishuAccount?: string
  themeId?: string
  apiBase?: string
  defaultCoverUrl?: string
  notes?: string
  isDefault?: boolean
}

export interface WechatAccount extends Omit<WechatAccountPayload, 'appSecret'> {
  accountId: number
  scope?: string
  appSecretMasked: string
  isActive?: boolean
  authorizedUserIds?: number[]
  lastTestStatus: string
  lastTestMessage: string
  lastTestAt: string | null
  createdAt: string | null
  updatedAt: string | null
}

export interface WechatDraftPayload {
  accountId: number
  platformContentId?: number
  title: string
  author?: string
  digest?: string
  rawContent: string
  coverUrl?: string
  contentSourceUrl?: string
  style?: string
  idempotencyKey?: string
}

export interface WechatDraftRecord extends WechatDraftPayload {
  draftId: number
  wechatMediaId: string
  thumbMediaId: string
  formattedHtml?: string
  status: string
  errorCode: string
  errorMessage: string
  createdAt: string | null
  updatedAt: string | null
}

export interface WechatPreflightResult {
  canSend: boolean
  issues: Array<{ level: string; code: string; message: string; suggestion: string }>
  imageCount: number
  selectedCoverUrl: string
}

export async function listWechatAccounts(): Promise<{ code: number; data: { items: WechatAccount[] } }> {
  const res = await api.get('/api/wechat/accounts')
  return res.data
}

export async function createWechatAccount(params: WechatAccountPayload): Promise<{ code: number; data: WechatAccount; message: string }> {
  const res = await api.post('/api/wechat/accounts', params)
  return res.data
}

export async function updateWechatAccount(accountId: number, params: WechatAccountPayload): Promise<{ code: number; data: WechatAccount; message: string }> {
  const res = await api.put(`/api/wechat/accounts/${accountId}`, params)
  return res.data
}

export async function deleteWechatAccount(accountId: number): Promise<{ code: number; data: { accountId: number; deleted: boolean }; message: string }> {
  const res = await api.delete(`/api/wechat/accounts/${accountId}`)
  return res.data
}

export async function testWechatAccount(accountId: number): Promise<{ code: number; data: { ok: boolean; errorCode?: string }; message: string }> {
  const res = await api.post(`/api/wechat/accounts/${accountId}/test`)
  return res.data
}

export async function listWechatThemes(params: { feishuAccount: string; apiBase?: string }) {
  const res = await api.post('/api/wechat/themes/list', params)
  return res.data
}

export async function previewWechatFormat(params: { title: string; rawContent: string; style?: string; accountId?: number; feishuAccount?: string; themeId?: string; apiBase?: string }) {
  const res = await api.post('/api/wechat/format/preview', params)
  return res.data
}

export async function preflightWechatDraft(params: { accountId?: number; title: string; digest?: string; rawContent: string; coverUrl?: string }): Promise<{ code: number; data: WechatPreflightResult }> {
  const res = await api.post('/api/wechat/drafts/preflight', params)
  return res.data
}

export async function sendWechatDraft(params: WechatDraftPayload): Promise<{ code: number; data: WechatDraftRecord; message: string }> {
  const res = await api.post('/api/wechat/drafts', params)
  return res.data
}

export async function listWechatDrafts(params: { page?: number; pageSize?: number; status?: string } = {}): Promise<{ code: number; data: { items: WechatDraftRecord[]; total: number; page: number; pageSize: number } }> {
  const res = await api.get('/api/wechat/drafts', { params })
  return res.data
}
