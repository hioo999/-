import { api } from './client'

export interface UnifiedAssetListParams {
  projectId?: number
  topicId?: number
  platformContentId?: number
  assetType?: string
  sourceType?: string
  tag?: string
  limit?: number
}

export interface UnifiedAssetCreateParams {
  assetType?: string
  sourceType?: string
  title?: string
  url?: string
  storagePath?: string
  projectId?: number
  topicId?: number
  platformContentId?: number
  metadata?: Record<string, any>
  tags?: string[]
}

export async function listUnifiedAssets(params: UnifiedAssetListParams = {}) {
  const res = await api.get('/api/assets', { params })
  return res.data
}

export async function createUnifiedAsset(params: UnifiedAssetCreateParams) {
  const res = await api.post('/api/assets', params)
  return res.data
}

export async function getUnifiedAsset(assetId: number) {
  const res = await api.get(`/api/assets/${assetId}`)
  return res.data
}

export async function downloadUnifiedAssetFile(assetId: number): Promise<Blob> {
  const res = await api.get(`/api/assets/${assetId}/file`, { responseType: 'blob' })
  return res.data
}

export async function deleteUnifiedAsset(assetId: number) {
  const res = await api.delete(`/api/assets/${assetId}`)
  return res.data
}

export async function reuseUnifiedAsset(assetId: number, params: { target?: string; platformContentId: number; slotIndex: number; insertToMarkdown?: boolean }) {
  const res = await api.post(`/api/assets/${assetId}/reuse`, params)
  return res.data
}
