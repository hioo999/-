import { api, apiBaseURL } from './client'
import type { VideoAssetAnalysisItem } from './videoAssets.types'
export * from './auth'
export * from './personas'
export * from './strategy'
export * from './dashboard.api'
export * from './teleprompter.api'
export * from './wechat.api'
export * from './platformContent.api'
export * from './tasks.api'
export * from './assets.api'
export * from './videoAssets.types'
export * from './videoAip.api'

// ─── 内容解析 ──────────────────────────────────────────────

export async function parseUrl(url: string) {
  const res = await api.post('/api/copilot/parse', { url })
  return res.data
}

export async function parseText(text: string) {
  const res = await api.post('/api/copilot/parse', { text })
  return res.data
}

export async function parseFile(file: File) {
  const form = new FormData()
  form.append('file', file)
  const res = await api.post('/api/copilot/parse-file', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

// ─── 一键生成 ──────────────────────────────────────────────

export interface GenerateParams {
  extracted_content: string
  persona_id: number
  target_platform: string
  extra_requirements?: string
  cover_style?: string
  column_id?: number
  prompt_template_id?: number
  prompt_template_key?: string
  prompt_template_category?: string
  text_model_config_id?: number
  cover_prompt_template_id?: number
  cover_model_config_id?: number
  video_prompt_template_id?: number
  video_model_config_id?: number
  cover_aspect_ratio?: string
  cover_title?: string
  video_aspect_ratio?: string
  video_duration?: string
  video_workflow_type?: string
}

export async function generateFullCase(params: GenerateParams) {
  const res = await api.post('/api/copilot/generate', params)
  return res.data
}

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

// ─── 平台化内容工作台 ────────────────────────────────────────

export interface IpProjectData {
  projectId: number
  name: string
  ipType: string
  positioning: string
  targetAudience: string
  defaultPlatforms: string[]
  voiceStyle: Record<string, any>
  status: string
  createdAt: string | null
  updatedAt: string | null
}

export interface ContentTopicData {
  topicId: number
  projectId: number
  title: string
  inputSourceType: string
  targetPlatforms: string[]
  status: string
  priority: string
  createdAt: string | null
  updatedAt: string | null
}

export interface PlatformContentData {
  contentId: number
  projectId: number
  topicId: number
  materialId: number
  platform: string
  contentType: string
  title: string
  subtitle: string
  author: string
  summary: string
  coverPrompt: string
  coverAssetId: number
  imageSlots: Array<Record<string, any>>
  tags: string[]
  complianceRisks: Array<Record<string, any> | string>
  status: string
  version: number
  content?: Record<string, any>
  contentHtml?: string
  markdownSnapshot?: string
  createdAt: string | null
  updatedAt: string | null
}

export interface PlatformPublishConfigData {
  configId?: number
  platform: string
  name: string
  accountLabel?: string
  apiBase?: string
  authType?: string
  credentials?: string
  credentialsMasked?: string
  status?: string
  notes?: string
  isActive?: boolean
  createdAt?: string | null
  updatedAt?: string | null
}

export interface CharacterProfileData {
  characterId?: number
  projectId?: number
  name: string
  role?: string
  identity?: string
  personality?: string
  speakingStyle?: string
  catchphrase?: string
  referenceImages?: string[]
  profile?: Record<string, any>
  status?: string
  createdAt?: string | null
  updatedAt?: string | null
}

export interface StoryboardRecordData {
  storyboardId?: number
  projectId?: number
  topicId?: number
  platformContentId?: number
  title: string
  storyboardType?: string
  frames?: Array<Record<string, any>>
  assets?: Array<Record<string, any>>
  status?: string
  createdAt?: string | null
  updatedAt?: string | null
}

export interface WechatArticleGenerateParams {
  projectId?: number
  topicId?: number
  projectName?: string
  topicTitle?: string
  inputType: 'topic' | 'url' | 'text'
  sourceUrl?: string
  rawText?: string
  theme?: string
  promptTemplateId?: number
  textModelConfigId?: number
  extraRequirements?: string
}

export interface PlatformTextGenerateParams {
  projectId?: number
  topicId?: number
  projectName?: string
  topicTitle?: string
  inputType: 'topic' | 'url' | 'text'
  sourceUrl?: string
  rawText?: string
  theme?: string
  promptTemplateId?: number
  textModelConfigId?: number
  extraRequirements?: string
  targetPlatform?: string
}

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

export interface PlatformWorkspaceOverviewData {
  workspaces: Array<{
    platform: string
    label: string
    contentType: string
    status: string
    contentCount: number
    recentContents: PlatformContentData[]
  }>
  metrics: {
    projects: number
    topics: number
    contents: number
    assets: number
    tasks: number
    generationRecords: number
    failedTasks: number
    deletedAssetsRetained: number
  }
  statusCounts: Record<string, number>
  recentContents: PlatformContentData[]
  recentTasks: Array<Record<string, any>>
  retentionPolicy: {
    contentDelete: string
    assetDelete: string
    taskRetention: string
    generationRecordRetention: string
    message: string
  }
  lastActivityAt: string | null
}

export async function listIpProjects(): Promise<{ code: number; data: { items: IpProjectData[]; total: number } }> {
  const res = await api.get('/api/projects')
  return res.data
}

export async function createIpProject(params: Partial<IpProjectData> & { name: string }): Promise<{ code: number; data: IpProjectData; message: string }> {
  const res = await api.post('/api/projects', params)
  return res.data
}

export async function listProjectTopics(projectId: number): Promise<{ code: number; data: { items: ContentTopicData[]; total: number } }> {
  const res = await api.get(`/api/projects/${projectId}/topics`)
  return res.data
}

export async function createContentTopic(projectId: number, params: { title: string; inputSourceType?: string; targetPlatforms?: string[]; priority?: string }): Promise<{ code: number; data: ContentTopicData; message: string }> {
  const res = await api.post(`/api/projects/${projectId}/topics`, params)
  return res.data
}

export async function listPlatformContents(params: { projectId?: number; topicId?: number; platform?: string; contentType?: string; status?: string; limit?: number } = {}): Promise<{ code: number; data: { items: PlatformContentData[]; total: number } }> {
  const res = await api.get('/api/platform-contents', { params })
  return res.data
}

export async function getPlatformContent(contentId: number) {
  const res = await api.get(`/api/platform-contents/${contentId}`)
  return res.data
}

export async function updatePlatformContent(contentId: number, params: Partial<PlatformContentData> & { content?: Record<string, any> }) {
  const res = await api.put(`/api/platform-contents/${contentId}`, params)
  return res.data
}

export async function exportPlatformContent(contentId: number) {
  const res = await api.get(`/api/platform-contents/${contentId}/export`)
  return res.data
}

export async function downloadPlatformContentPackage(contentId: number): Promise<Blob> {
  const res = await api.get(`/api/platform-contents/${contentId}/download-package`, { responseType: 'blob' })
  return res.data
}

export async function getPlatformWorkspaceOverview(): Promise<{ code: number; data: PlatformWorkspaceOverviewData }> {
  const res = await api.get('/api/platform-workspace/overview')
  return res.data
}

export async function deletePlatformContent(contentId: number): Promise<{ code: number; data: { contentId: number; deleted: boolean; softDeletedAssets: number; retainedTasks: number; retainedGenerationRecords: number }; message: string }> {
  const res = await api.delete(`/api/platform-contents/${contentId}`)
  return res.data
}

export async function generateWechatArticle(params: WechatArticleGenerateParams) {
  const res = await api.post('/api/wechat/articles/generate', params)
  return res.data
}

export async function generateXiaohongshuNote(params: PlatformTextGenerateParams) {
  const res = await api.post('/api/xiaohongshu/notes', params)
  return res.data
}

export async function generateShortVideoScript(params: PlatformTextGenerateParams) {
  const res = await api.post('/api/short-video/scripts', params)
  return res.data
}

export async function generatePlatformContentSlotImage(contentId: number, slotIndex: number, params: { prompt?: string; workflow?: string; imageModelConfigId?: number; width?: number; height?: number; insertToMarkdown?: boolean; extra?: Record<string, any> }) {
  const res = await api.post(`/api/platform-contents/${contentId}/image-slots/${slotIndex}/generate`, params)
  return res.data
}

export async function addPlatformContentImageAsset(contentId: number, params: { imageUrl: string; title?: string; slotIndex?: number; tags?: string[]; insertToMarkdown?: boolean }) {
  const res = await api.post(`/api/platform-contents/${contentId}/image-assets`, params)
  return res.data
}

export async function uploadPlatformContentImageAsset(contentId: number, params: { file: File; title?: string; slotIndex?: number; tags?: string[]; insertToMarkdown?: boolean }) {
  const form = new FormData()
  form.append('file', params.file)
  form.append('title', params.title || '')
  form.append('slotIndex', String(params.slotIndex ?? -1))
  form.append('insertToMarkdown', String(params.insertToMarkdown ?? false))
  form.append('tags', (params.tags || []).join(','))
  const res = await api.post(`/api/platform-contents/${contentId}/image-upload`, form, { headers: { 'Content-Type': 'multipart/form-data' } })
  return res.data
}

export async function importPlatformContentToTeleprompter(params: { platformContentId: number; settings?: Record<string, any> }) {
  const res = await api.post('/api/teleprompter/import', params)
  return res.data
}

export async function getWechatArticle(contentId: number) {
  const res = await api.get(`/api/wechat/articles/${contentId}`)
  return res.data
}

export async function updateWechatArticle(contentId: number, params: Partial<PlatformContentData>) {
  const res = await api.put(`/api/wechat/articles/${contentId}`, params)
  return res.data
}

export async function listUnifiedTasks(params: { projectId?: number; topicId?: number; platformContentId?: number; taskType?: string; status?: string; limit?: number } = {}) {
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

export async function listUnifiedAssets(params: { projectId?: number; topicId?: number; platformContentId?: number; assetType?: string; sourceType?: string; tag?: string; limit?: number } = {}) {
  const res = await api.get('/api/assets', { params })
  return res.data
}

export async function listGenerationRecords(params: { taskId?: number; projectId?: number; topicId?: number; platformContentId?: number; parseStatus?: string; includeRaw?: boolean; limit?: number } = {}): Promise<{ code: number; data: { items: GenerationRecordData[]; total: number } }> {
  const res = await api.get('/api/generation-records', { params })
  return res.data
}

export async function createUnifiedAsset(params: { assetType?: string; sourceType?: string; title?: string; url?: string; storagePath?: string; projectId?: number; topicId?: number; platformContentId?: number; metadata?: Record<string, any>; tags?: string[] }) {
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

export async function generateWechatArticleSlotImage(contentId: number, slotIndex: number, params: { prompt?: string; workflow?: string; imageModelConfigId?: number; width?: number; height?: number; insertToMarkdown?: boolean; extra?: Record<string, any> }) {
  const res = await api.post(`/api/wechat/articles/${contentId}/image-slots/${slotIndex}/generate`, params)
  return res.data
}

export async function generateWechatArticleCover(contentId: number, params: { prompt?: string; workflow?: string; imageModelConfigId?: number; width?: number; height?: number; extra?: Record<string, any> } = {}) {
  const res = await api.post(`/api/wechat/articles/${contentId}/cover/generate`, params)
  return res.data
}

export async function setWechatArticleCover(contentId: number, params: { assetId?: number; imageUrl?: string }) {
  const res = await api.post(`/api/wechat/articles/${contentId}/cover`, params)
  return res.data
}

export async function insertWechatArticleSlotImage(contentId: number, slotIndex: number, params: { assetId?: number; imageUrl?: string; altText?: string; insertToMarkdown?: boolean }) {
  const res = await api.post(`/api/wechat/articles/${contentId}/image-slots/${slotIndex}/insert`, params)
  return res.data
}

export async function removeWechatArticleSlotAsset(contentId: number, slotIndex: number) {
  const res = await api.delete(`/api/wechat/articles/${contentId}/image-slots/${slotIndex}/asset`)
  return res.data
}

export async function listPlatformPublishConfigs(platform = '') {
  const res = await api.get('/api/platform-publish-configs', { params: { platform } })
  return res.data
}

export async function createPlatformPublishConfig(data: PlatformPublishConfigData) {
  const res = await api.post('/api/platform-publish-configs', data)
  return res.data
}

export async function updatePlatformPublishConfig(configId: number, data: PlatformPublishConfigData) {
  const res = await api.put(`/api/platform-publish-configs/${configId}`, data)
  return res.data
}

export async function deletePlatformPublishConfig(configId: number) {
  const res = await api.delete(`/api/platform-publish-configs/${configId}`)
  return res.data
}

export async function listCharacterProfiles(params: { projectId?: number } = {}) {
  const res = await api.get('/api/characters', { params })
  return res.data
}

export async function createCharacterProfile(data: CharacterProfileData) {
  const res = await api.post('/api/characters', data)
  return res.data
}

export async function updateCharacterProfile(characterId: number, data: CharacterProfileData) {
  const res = await api.put(`/api/characters/${characterId}`, data)
  return res.data
}

export async function deleteCharacterProfile(characterId: number) {
  const res = await api.delete(`/api/characters/${characterId}`)
  return res.data
}

export async function listStoryboardRecords(params: { projectId?: number; topicId?: number; platformContentId?: number; storyboardType?: string } = {}) {
  const res = await api.get('/api/storyboards', { params })
  return res.data
}

export async function createStoryboardRecord(data: StoryboardRecordData) {
  const res = await api.post('/api/storyboards', data)
  return res.data
}

export async function updateStoryboardRecord(storyboardId: number, data: StoryboardRecordData) {
  const res = await api.put(`/api/storyboards/${storyboardId}`, data)
  return res.data
}

export async function deleteStoryboardRecord(storyboardId: number) {
  const res = await api.delete(`/api/storyboards/${storyboardId}`)
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

// ─── 微信公众号排版与草稿 ──────────────────────────────────────

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

export async function preflightWechatDraft(params: { accountId?: number; title: string; digest?: string; rawContent: string; coverUrl?: string }) {
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

// ─── Copilot 流式修改 ──────────────────────────────────────

export interface ModifyParams {
  content_type: string
  current_content: string
  user_instruction: string
  persona_id?: number
}

function readStreamContent(value: unknown): string | null {
  if (!value || typeof value !== 'object' || !('content' in value)) {
    return null
  }

  const content = (value as { content?: unknown }).content
  return typeof content === 'string' ? content : null
}

async function parseStreamEventContent(data: string): Promise<string | null> {
  const parsed: unknown = await new Response(data, {
    headers: { 'Content-Type': 'application/json' },
  }).json()
  return readStreamContent(parsed)
}

export async function copilotModifyStream(
  params: ModifyParams,
  onChunk: (text: string) => void,
  onDone: () => void,
  onError: (err: string) => void
) {
  try {
    const response = await fetch(
      `${apiBaseURL}/api/copilot/modify`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
      }
    )

    if (!response.ok) {
      onError(`请求失败: ${response.status}`)
      return
    }

    const reader = response.body?.getReader()
    if (!reader) {
      onError('无法获取响应流')
      return
    }

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6).trim()
          if (data === '[DONE]') {
            onDone()
            return
          }
          try {
            const content = await parseStreamEventContent(data)
            if (content) {
              onChunk(content)
            }
          } catch {
            // skip
          }
        }
      }
    }
    onDone()
  } catch (err: any) {
    onError(err.message || '网络错误')
  }
}

// ─── AI短视频工作流路由 ──────────────────────────────────────

export interface ShortVideoWorkflowParams {
  user_input: string
  requested_intent?: string
  subject_name?: string
  platform?: string
  aspect_ratio?: string
  duration?: string
  model?: string
  style?: string
  target_audience?: string
  core_message?: string
}

export interface ShortVideoIntentOption {
  key: string
  label: string
  command: string
  template_doc: string
  keywords: string[]
  steps: string[]
}

export interface ShortVideoWorkflowStep {
  key: string
  label: string
  description: string
  prompt: string
}

export interface ShortVideoWorkflowResult {
  intent: {
    intent: string
    label: string
    confidence: number
    matched_keywords: string[]
    source: string
  }
  workflow: null | {
    key: string
    label: string
    recommended_command: string
    template_doc: string
  }
  variables: Record<string, string>
  steps: ShortVideoWorkflowStep[]
  questions?: string[]
  next_actions: string[]
}

export async function listShortVideoIntents(): Promise<{ code: number; data: ShortVideoIntentOption[] }> {
  const res = await api.get('/api/short-video/intents')
  return res.data
}

export async function buildShortVideoWorkflow(
  params: ShortVideoWorkflowParams
): Promise<{ code: number; data: ShortVideoWorkflowResult }> {
  const res = await api.post('/api/short-video/workflow', params)
  return res.data
}

export interface ShortVideoProjectCreateParams {
  title: string
  subject_name?: string
  intent_key?: string
  intent_label?: string
  confidence?: number
  platform?: string
  aspect_ratio?: string
  duration?: string
  model?: string
  style?: string
  target_audience?: string
  core_message?: string
  user_input?: string
  workflow?: ShortVideoWorkflowResult
  archive_markdown?: string
  notes?: string
}

export interface ShortVideoProjectSummary {
  id: number
  title: string
  subject_name: string
  intent_key: string
  intent_label: string
  confidence: string
  platform: string
  aspect_ratio: string
  duration: string
  model: string
  style: string
  target_audience: string
  core_message: string
  user_input: string
  notes: string
  is_active: boolean
  created_at: string | null
  updated_at: string | null
}

export async function saveShortVideoProject(
  params: ShortVideoProjectCreateParams
): Promise<{ code: number; data: ShortVideoProjectSummary; message: string }> {
  const res = await api.post('/api/short-video/projects', params)
  return res.data
}

export async function listShortVideoProjects(limit = 50): Promise<{ code: number; data: ShortVideoProjectSummary[] }> {
  const res = await api.get('/api/short-video/projects', { params: { limit } })
  return res.data
}

// ─── 职场反转剧编剧 ────────────────────────────────────────

export interface ReversalCharacter {
  name: string
  gender?: string
  role?: string
  personality?: string
  catchphrase?: string
}

export interface ReversalDramaParams {
  product_name: string
  product_function: string
  pain_point: string
  characters?: ReversalCharacter[] | null
  platform?: string
  duration?: string
  extra_requirements?: string
}

export interface ReversalScene {
  shot: number
  duration: string
  visual: string
  dialogue: string
  bgm: string
}

export interface ReversalChecklistItem {
  item: string
  passed: boolean
}

export interface ReversalDramaResult {
  history_id: number
  raw_markdown: string
  overview: {
    title?: string
    duration?: string
    pain_point?: string
    product?: string
    reversal_type?: string
    characters?: string
  }
  scenes: ReversalScene[]
  ending_subtitle: string
  checklist: ReversalChecklistItem[]
}

export async function generateReversalDrama(
  params: ReversalDramaParams
): Promise<{ code: number; data: ReversalDramaResult }> {
  const res = await api.post('/api/copilot/reversal-drama/generate', params)
  return res.data
}

export interface ReversalDramaHistoryItem {
  id: number | string
  createdAt: string
  title: string
  productName: string
  painPoint: string
  params: ReversalDramaParams
  result: ReversalDramaResult
}

export async function listReversalDramaHistory(limit = 30): Promise<{ code: number; data: ReversalDramaHistoryItem[] }> {
  const res = await api.get('/api/copilot/reversal-drama/history', { params: { limit } })
  return res.data
}

export async function deleteReversalDramaHistory(id: number | string): Promise<{ code: number; message: string }> {
  const res = await api.delete(`/api/copilot/reversal-drama/history/${id}`)
  return res.data
}

export async function clearReversalDramaHistory(): Promise<{ code: number; message: string }> {
  const res = await api.delete('/api/copilot/reversal-drama/history')
  return res.data
}

// ─── 历史记录 ──────────────────────────────────────────────

export async function listHistory(limit = 20) {
  const res = await api.get('/api/copilot/history', { params: { limit } })
  return res.data
}

export async function getHistory(id: number) {
  const res = await api.get(`/api/copilot/history/${id}`)
  return res.data
}

// ─── 视频引擎（video_engine / Pixelle） ────────────────────

export interface VideoPipelinesResponse {
  ready: boolean
  error: string | null
  pipelines: string[]
}

export interface VideoGenerateParams {
  text: string
  pipeline?: string
  mode?: 'generate' | 'fixed'
  n_scenes?: number
  min_narration_words?: number
  max_narration_words?: number
  template?: string
  extra?: Record<string, any>
}

export interface VideoTemplateOption {
  path: string
  name: string
  size: string
  width: number
  height: number
  orientation: 'portrait' | 'landscape' | 'square'
  is_standard: boolean
  type: 'static' | 'image' | 'video'
  params: Record<string, { type: string; default: any; label: string }>
  media_width: number | null
  media_height: number | null
  error?: string
}

export interface VideoWorkflowOption {
  name: string
  display_name?: string
  source: string
  path?: string
  key: string
  workflow_id?: string
}

export interface VideoTtsVoiceOption {
  id: string
  label_key?: string
  locale: string
  gender: string
}

export interface VideoOptionsResponse {
  ready: boolean
  error: string | null
  pipelines: string[]
  templates: VideoTemplateOption[]
  workflows: {
    media: VideoWorkflowOption[]
    tts: VideoWorkflowOption[]
    image_analysis: VideoWorkflowOption[]
    video_analysis: VideoWorkflowOption[]
  }
  workflow_error: any
  tts_voices: VideoTtsVoiceOption[]
  bgm: string[]
}

export interface VideoTaskStatus {
  task_id: string
  pipeline: string
  status: 'pending' | 'running' | 'succeeded' | 'failed'
  progress: number
  current_event: string | null
  error: string | null
  video_path: string | null
  media_type: 'image' | 'video' | null
  media_url: string | null
  media_path: string | null
  duration: number | null
  file_size: number | null
}

export async function getVideoPipelines(): Promise<VideoPipelinesResponse> {
  const res = await api.get('/api/video/pipelines')
  return res.data
}

export async function getVideoOptions(): Promise<VideoOptionsResponse> {
  const res = await api.get('/api/video/options')
  return res.data
}

export async function submitVideoGenerate(
  params: VideoGenerateParams
): Promise<{ task_id: string; status: string; pipeline: string }> {
  const res = await api.post('/api/video/generate', params)
  return res.data
}

export async function getVideoTask(taskId: string): Promise<VideoTaskStatus> {
  const res = await api.get(`/api/video/tasks/${taskId}`)
  return res.data
}

export async function analyzeVideoAssets(
  files: File[],
  source = 'runninghub'
): Promise<{ assets: VideoAssetAnalysisItem[]; extracted_content: string }> {
  const form = new FormData()
  files.forEach((file) => form.append('files', file))
  form.append('source', source)
  const res = await api.post('/api/video/analyze-assets', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export async function submitAssetVideoGenerate(params: {
  files: File[]
  video_title?: string
  intent?: string
  duration?: number
  source?: string
  voice_id?: string
  tts_speed?: number
  bgm_path?: string
  bgm_volume?: number
  bgm_mode?: string
}): Promise<{ task_id: string; status: string; pipeline: string }> {
  const form = new FormData()
  params.files.forEach((file) => form.append('files', file))
  form.append('video_title', params.video_title || '')
  form.append('intent', params.intent || '')
  form.append('duration', String(params.duration ?? 30))
  form.append('source', params.source || 'runninghub')
  form.append('voice_id', params.voice_id || 'zh-CN-YunjianNeural')
  form.append('tts_speed', String(params.tts_speed ?? 1.2))
  form.append('bgm_path', params.bgm_path || '')
  form.append('bgm_volume', String(params.bgm_volume ?? 0.2))
  form.append('bgm_mode', params.bgm_mode || 'loop')
  const res = await api.post('/api/video/generate-from-assets', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export function videoTaskFileUrl(taskId: string): string {
  return `${apiBaseURL}/api/video/tasks/${taskId}/file`
}

export function videoTaskMediaFileUrl(taskId: string): string {
  return `${apiBaseURL}/api/video/tasks/${taskId}/media-file`
}

// ─── Sprint 1 全案底座 Mock API ─────────────────────────────

export interface Sprint1IpAssetPayload {
  name: string
  type: string
  industry: string
  targetAudience: string
  businessGoal: string
  mainPlatforms: string[]
  secondaryPlatforms: string[]
  tone: string
  visualStyle: string
  conversionPath: string
  forbiddenExpressions: string
}

export interface Sprint1IpAsset extends Sprint1IpAssetPayload {
  id: string
  profileStatus: 'complete' | 'incomplete'
  createdAt: string
  updatedAt: string
}

export interface Sprint1Strategy {
  strategyId: string
  ipId: string
  positioning: string
  targetUserProfile: string
  corePainPoints: string[]
  platformRoles: Record<string, string>
  conversionPath: string
  forbiddenDirections: string[]
  inputSnapshot: Sprint1IpAsset
  taskId: string
  createdAt: string
  updatedAt: string
}

export interface Sprint1StrategyPayload {
  positioning: string
  targetUserProfile: string
  corePainPoints: string[]
  platformRoles: Record<string, string>
  conversionPath: string
  forbiddenDirections: string[]
}

export interface Sprint1Column {
  id: string
  ipId: string
  strategyId: string
  name: string
  positioning: string
  platforms: string[]
  contentFormat: string
  frequency: string
  conversionAction: string
  createdAt: string
  updatedAt: string
}

export interface Sprint1ColumnPayload {
  name: string
  positioning: string
  platforms: string[]
  contentFormat: string
  frequency: string
  conversionAction: string
}

export interface Sprint1Topic {
  id: string
  ipId: string
  columnId: string
  title: string
  platforms: string[]
  contentGoal: string
  userPainPoint: string
  coreViewpoint: string
  status: string
  priority: string
  createdAt: string
  updatedAt: string
}

export interface Sprint1DraftPayload {
  painPoint: string
  coreViewpoint: string
  logic: string
  cases: string
  goldenSentences: string[]
  conversionAction: string
  forbiddenExpressions: string
  status: string
}

export interface Sprint1Draft extends Sprint1DraftPayload {
  draftId: string
  topicId: string
  ipId: string
  version: number
  taskId: string
  createdAt: string
  updatedAt: string
}

export interface Sprint1Material {
  materialId: string
  ipId: string
  filename: string
  contentType: string
  url: string
  status: string
  createdAt: string
}

export interface Sprint1Task {
  taskId: string
  type: string
  status: 'pending' | 'running' | 'succeeded' | 'failed'
  progress: number
  inputSnapshot: Record<string, any>
  outputSnapshot: any
  errorCode: string
  errorMessage: string
  createdAt: string
  updatedAt: string
}

export async function createSprint1IpAsset(params: Sprint1IpAssetPayload): Promise<{ code: number; data: { ipId: string; asset: Sprint1IpAsset }; message: string }> {
  const res = await api.post('/api/ip-assets', params)
  return res.data
}

export async function updateSprint1IpAsset(id: string, params: Sprint1IpAssetPayload): Promise<{ code: number; data: Sprint1IpAsset; message: string }> {
  const res = await api.put(`/api/ip-assets/${id}`, params)
  return res.data
}

export async function listSprint1IpAssets(params: { page?: number; pageSize?: number; type?: string } = {}): Promise<{ code: number; data: { items: Sprint1IpAsset[]; total: number; page: number; pageSize: number } }> {
  const res = await api.get('/api/ip-assets', { params })
  return res.data
}

export async function getSprint1IpAsset(ipId: string): Promise<{ code: number; data: Sprint1IpAsset }> {
  const res = await api.get(`/api/ip-assets/${ipId}`)
  return res.data
}

export interface Sprint1StrategyPayload {
  positioning: string
  targetUserProfile: string
  corePainPoints: string[]
  platformRoles: Record<string, string>
  conversionPath: string
  forbiddenDirections: string[]
}

export async function listSprint1Strategies(params: { ipId?: string } = {}): Promise<{ code: number; data: { items: Sprint1Strategy[]; total: number } }> {
  const res = await api.get('/api/strategies', { params })
  return res.data
}

export async function updateSprint1Strategy(id: string, params: Sprint1StrategyPayload): Promise<{ code: number; data: Sprint1Strategy; message: string }> {
  const res = await api.put(`/api/strategies/${id}`, params)
  return res.data
}

export interface Sprint1ColumnPayload {
  name: string
  positioning: string
  platforms: string[]
  contentFormat: string
  frequency: string
  conversionAction: string
}

export async function listSprint1Columns(params: { ipId?: string } = {}): Promise<{ code: number; data: { items: Sprint1Column[]; total: number } }> {
  const res = await api.get('/api/columns', { params })
  return res.data
}

export async function updateSprint1Column(id: string, params: Sprint1ColumnPayload): Promise<{ code: number; data: Sprint1Column; message: string }> {
  const res = await api.put(`/api/columns/${id}`, params)
  return res.data
}

export async function deleteSprint1Column(id: string): Promise<{ code: number; data: { columnId: string; deleted: boolean }; message: string }> {
  const res = await api.delete(`/api/columns/${id}`)
  return res.data
}

export async function listSprint1Drafts(params: { ipId?: string; topicId?: string } = {}): Promise<{ code: number; data: { items: Sprint1Draft[]; total: number } }> {
  const res = await api.get('/api/content-drafts', { params })
  return res.data
}

export async function listSprint1Topics(params: { ipId?: string; platform?: string; status?: string } = {}): Promise<{ code: number; data: { items: Sprint1Topic[]; total: number } }> {
  const res = await api.get('/api/topics', { params })
  return res.data
}

export async function generateSprint1Strategy(ipId: string): Promise<{ code: number; data: Sprint1Strategy }> {
  const res = await api.post('/api/strategies/generate', { ipId })
  return res.data
}

export async function generateSprint1Columns(params: { ipId: string; strategyId?: string }): Promise<{ code: number; data: { taskId: string; items: Sprint1Column[] } }> {
  const res = await api.post('/api/columns/generate', params)
  return res.data
}

export async function generateSprint1Topics(params: { ipId: string; columnId?: string; count?: number }): Promise<{ code: number; data: { taskId: string; items: Sprint1Topic[] } }> {
  const res = await api.post('/api/topics/generate', params)
  return res.data
}

export async function generateSprint1Draft(params: { ipId: string; topicId: string }): Promise<{ code: number; data: Sprint1Draft }> {
  const res = await api.post('/api/content-drafts/generate', params)
  return res.data
}

export async function updateSprint1Draft(id: string, params: Sprint1DraftPayload): Promise<{ code: number; data: Sprint1Draft; message: string }> {
  const res = await api.put(`/api/content-drafts/${id}`, params)
  return res.data
}

export async function uploadSprint1Material(params: { ipId?: string; file: File }): Promise<{ code: number; data: Sprint1Material; message: string }> {
  const form = new FormData()
  form.append('ipId', params.ipId || '')
  form.append('file', params.file)
  const res = await api.post('/api/materials/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export async function getSprint1GenerationTask(taskId: string): Promise<{ code: number; data: Sprint1Task }> {
  const res = await api.get(`/api/generation-tasks/${taskId}`)
  return res.data
}

// ─── 在线提词器 ──────────────────────────────────────────────

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

export async function reportTeleprompterEvent(params: { eventName: string; eventTime?: string; sessionId?: string; properties?: Record<string, unknown> }) {
  const res = await api.post('/api/teleprompter/analytics/events', params)
  return res.data
}

export default api
