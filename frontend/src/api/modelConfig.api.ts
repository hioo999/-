import { api } from './client'

export interface AIModelConfigData {
  id?: number
  user_id?: number
  gateway_id?: number
  name: string
  model_type: string
  provider: string
  api_key?: string
  api_key_masked?: string
  base_url: string
  model_id: string
  is_openai_compatible?: boolean
  is_default?: boolean
  is_active?: boolean
  recommendation_label?: string
  recommendation_reason?: string
  risk_note?: string
  last_seen_at?: string | null
  resolved_by?: string
  timeout_seconds?: number
  max_retries?: number
  sort_order?: number
  notes?: string
}

export interface ModelGatewayData {
  id?: number
  user_id?: number
  scope?: 'user' | 'global'
  name: string
  provider_type?: string
  base_url: string
  api_key?: string
  api_key_masked?: string
  is_active?: boolean
  last_test_status?: string
  last_test_message?: string
  last_model_count?: number
  last_synced_at?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface ModelDefaultsData {
  text?: { personal: AIModelConfigData | null; global: AIModelConfigData | null; resolved: AIModelConfigData | null }
  image?: { personal: AIModelConfigData | null; global: AIModelConfigData | null; resolved: AIModelConfigData | null }
  video?: { personal: AIModelConfigData | null; global: AIModelConfigData | null; resolved: AIModelConfigData | null }
  multimodal?: { personal: AIModelConfigData | null; global: AIModelConfigData | null; resolved: AIModelConfigData | null }
}

export async function listModelConfigs(modelType = '') {
  const res = await api.get('/api/copilot/model-configs', { params: { model_type: modelType } })
  return res.data
}

export async function createModelConfig(data: AIModelConfigData) {
  const res = await api.post('/api/copilot/model-configs', data)
  return res.data
}

export async function getModelConfig(id: number) {
  const res = await api.get(`/api/copilot/model-configs/${id}`)
  return res.data
}

export async function updateModelConfig(id: number, data: AIModelConfigData) {
  const res = await api.put(`/api/copilot/model-configs/${id}`, data)
  return res.data
}

export async function deleteModelConfig(id: number) {
  const res = await api.delete(`/api/copilot/model-configs/${id}`)
  return res.data
}

export async function listModelGateways() {
  const res = await api.get('/api/model-gateways')
  return res.data
}

export async function createModelGateway(data: ModelGatewayData) {
  const res = await api.post('/api/model-gateways', data)
  return res.data
}

export async function updateModelGateway(id: number, data: ModelGatewayData) {
  const res = await api.put(`/api/model-gateways/${id}`, data)
  return res.data
}

export async function deleteModelGateway(id: number) {
  const res = await api.delete(`/api/model-gateways/${id}`)
  return res.data
}

export async function testModelGateway(id: number) {
  const res = await api.post(`/api/model-gateways/${id}/test`)
  return res.data
}

export async function syncModelGatewayModels(id: number) {
  const res = await api.post(`/api/model-gateways/${id}/sync-models`)
  return res.data
}

export async function listModelCatalog(modelType = '') {
  const res = await api.get('/api/models/catalog', { params: { model_type: modelType } })
  return res.data
}

export async function updateModelCatalogItem(id: number, data: Partial<AIModelConfigData>) {
  const res = await api.patch(`/api/models/catalog/${id}`, data)
  return res.data
}

export async function getModelDefaults() {
  const res = await api.get('/api/model-defaults')
  return res.data
}

export async function setModelDefault(modelType: string, modelConfigId: number) {
  const res = await api.put('/api/model-defaults', { model_type: modelType, model_config_id: modelConfigId })
  return res.data
}

export async function setGlobalModelDefault(modelType: string, modelConfigId: number) {
  const res = await api.put('/api/admin/model-defaults', { model_type: modelType, model_config_id: modelConfigId })
  return res.data
}
