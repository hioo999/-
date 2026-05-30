import { api, apiBaseURL } from './client'
export * from './auth'

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
}

export async function listPromptTemplateCategories(templateType = '') {
  const res = await api.get('/api/copilot/prompt-template-categories', { params: { template_type: templateType } })
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

export async function createPromptTemplate(data: PromptTemplateData) {
  const res = await api.post('/api/copilot/prompt-templates', data)
  return res.data
}

export async function getPromptTemplate(id: number) {
  const res = await api.get(`/api/copilot/prompt-templates/${id}`)
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

export interface AIModelConfigData {
  id?: number
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

export interface VideoAipPlanParams {
  workflow_type: 'standard' | 'product_tvc' | 'drama'
  source_content?: string
  script_content?: string
  product_name?: string
  character_notes?: string
  media_notes?: string[]
  aspect_ratio?: string
  duration?: string
  style?: string
  user_requirements?: string
  video_prompt_template_id?: number
  video_model_config_id?: number
}

export interface VideoAipPlanStep {
  key: string
  title: string
  goal: string
  prompt: string
}

export interface VideoAipPlanResult {
  workflow_type: string
  title: string
  summary: string
  template?: PromptTemplateData | null
  model?: AIModelConfigData | null
  steps: VideoAipPlanStep[]
  handoff: string
}

export async function generateVideoAipPlan(params: VideoAipPlanParams) {
  const res = await api.post('/api/copilot/video-aip/plan', params)
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

// ─── 人设库 ────────────────────────────────────────────────

export interface PersonaData {
  id?: number
  name: string
  avatar_url?: string
  description?: string
  tone?: string
  speaking_style?: string
  catchphrase?: string
  target_audience?: string
  professional_field?: string
  reference_account?: string
  forbidden_words?: string
  full_prompt?: string
  sort_order?: number
  is_active?: boolean
}

export async function listPersonas() {
  const res = await api.get('/api/personas')
  return res.data
}

export async function createPersona(data: PersonaData) {
  const res = await api.post('/api/personas', data)
  return res.data
}

export async function updatePersona(id: number, data: PersonaData) {
  const res = await api.put(`/api/personas/${id}`, data)
  return res.data
}

export async function deletePersona(id: number) {
  const res = await api.delete(`/api/personas/${id}`)
  return res.data
}

// ─── 栏目库与内容策略 ────────────────────────────────────────

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
  duration: number | null
  file_size: number | null
}

export interface VideoAssetAnalysisItem {
  filename: string
  path: string
  type: 'image' | 'video' | 'unknown'
  description: string
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
