import { api } from './client'

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
