import { api } from './client'

export interface PromptTemplateCategoryData {
  id?: number
  key: string
  template_type?: string
  name: string
  description: string
  is_active?: boolean
  sort_order: number
}

export interface PromptTemplateData {
  id: number
  key: string
  template_type?: string
  category_key: string
  platform?: string
  scene?: string
  step?: string
  name: string
  description: string
  scenario: string
  output_structure: string
  writing_rules?: string[]
  prompt_body?: string
  user_prompt_hint?: string
  default_params_json?: string
  default_model_config_id?: number
  version: string
  is_default?: boolean
  is_active?: boolean
  sort_order: number
  change_note?: string
  versionId?: number
}

export interface PromptTemplateVersionData {
  versionId: number
  templateId: number
  templateKey: string
  version: string
  platform: string
  scene: string
  step: string
  outputStructure: string
  writingRules: string[]
  defaultParamsJson: string
  changeNote: string
  isActive: boolean
  createdAt: string | null
  promptBody?: string
}

export interface PromptTemplateMetricData {
  templateId: number
  templateType: string
  generationCount: number
  editedCount: number
  savedCount: number
  teleprompterOpenedCount: number
  editRate: number
  saveRate: number
  teleprompterRate: number
  lastGeneratedAt: string | null
}

export async function listPromptTemplateCategories(templateType = '') {
  const res = await api.get('/api/copilot/prompt-template-categories', templateType ? { params: { template_type: templateType } } : undefined)
  return res.data
}

export async function createPromptTemplateCategory(data: PromptTemplateCategoryData) {
  const res = await api.post('/api/copilot/prompt-template-categories', data)
  return res.data
}

export async function updatePromptTemplateCategory(categoryKey: string, data: PromptTemplateCategoryData) {
  const res = await api.put(`/api/copilot/prompt-template-categories/${categoryKey}`, data)
  return res.data
}

export async function deletePromptTemplateCategory(categoryKey: string) {
  const res = await api.delete(`/api/copilot/prompt-template-categories/${categoryKey}`)
  return res.data
}

export async function listPromptTemplates(categoryKey = '', templateType = '') {
  const res = await api.get('/api/copilot/prompt-templates', { params: { category_key: categoryKey, template_type: templateType } })
  return res.data
}

export async function listPromptTemplateMetrics(templateType = ''): Promise<{ code: number; data: PromptTemplateMetricData[] }> {
  const res = await api.get('/api/copilot/prompt-templates/metrics', templateType ? { params: { template_type: templateType } } : undefined)
  return res.data
}

export async function createPromptTemplate(data: PromptTemplateData) {
  const res = await api.post('/api/copilot/prompt-templates', data)
  return res.data
}

export async function getPromptTemplate(id: number) {
  const res = await api.get(`/api/copilot/prompt-templates/${id}`)
  return res.data
}

export async function listPromptTemplateVersions(id: number): Promise<{ code: number; data: { items: PromptTemplateVersionData[]; total: number } }> {
  const res = await api.get(`/api/copilot/prompt-templates/${id}/versions`)
  return res.data
}

export async function updatePromptTemplate(id: number, data: PromptTemplateData) {
  const res = await api.put(`/api/copilot/prompt-templates/${id}`, data)
  return res.data
}

export async function deletePromptTemplate(id: number) {
  const res = await api.delete(`/api/copilot/prompt-templates/${id}`)
  return res.data
}
