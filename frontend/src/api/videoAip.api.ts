import { api } from './client'
import type { AIModelConfigData } from './modelConfig.api'
import type { PromptTemplateData } from './promptTemplates.api'
import type { VideoAssetAnalysisItem } from './videoAssets.types'

export type VideoAipSourceAsset = VideoAssetAnalysisItem

export interface VideoAipPlanParams {
  title?: string
  workflow_type: 'standard' | 'product_tvc' | 'drama'
  source_content?: string
  script_content?: string
  product_name?: string
  character_notes?: string
  media_notes?: string[]
  source_assets?: VideoAipSourceAsset[]
  aspect_ratio?: string
  duration?: string
  style?: string
  user_requirements?: string
  text_model_config_id?: number
  video_prompt_template_id?: number
  video_model_config_id?: number
}

export interface VideoAipPlanStep {
  key: string
  title: string
  goal: string
  prompt: string
  task_type?: 'text' | 'image' | 'video'
  artifact_type?: string
  default_media_type?: 'image' | 'video'
  default_width?: number
  default_height?: number
}

export interface VideoAipStepTask {
  id: number
  project_id: number
  step_key: string
  title: string
  goal: string
  prompt: string
  status: 'pending' | 'running' | 'succeeded' | 'failed'
  output: Record<string, any>
  error_message: string
  sort_order: number
  created_at: string | null
  updated_at: string | null
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

export interface VideoAipProject {
  id: number
  title: string
  workflow_type: string
  status: 'planned' | 'running' | 'succeeded' | 'failed'
  source_content: string
  script_content: string
  product_name: string
  character_notes: string
  source_type: string
  source_ref_id: number
  source?: {
    type: string
    refId: number
    label: string
    title: string
    status: string
    meta?: string
    anchor?: string
  }
  source_assets: VideoAipSourceAsset[]
  params: Record<string, any>
  current_step_key: string
  plan?: VideoAipPlanResult
  steps?: VideoAipStepTask[]
  created_at: string | null
  updated_at: string | null
}

export async function generateVideoAipPlan(params: VideoAipPlanParams) {
  const res = await api.post('/api/copilot/video-aip/plan', params)
  return res.data
}

export async function createVideoAipProject(params: VideoAipPlanParams) {
  const res = await api.post('/api/copilot/video-aip/projects', params)
  return res.data
}

export async function createVideoAipProjectFromShortVideo(projectId: number, params: { title?: string; workflow_type?: string } = {}) {
  const res = await api.post(`/api/copilot/video-aip/projects/from-short-video/${projectId}`, params)
  return res.data
}

export async function createVideoAipProjectFromStoryboard(storyboardId: number, params: { title?: string; workflow_type?: string } = {}) {
  const res = await api.post(`/api/copilot/video-aip/projects/from-storyboard/${storyboardId}`, params)
  return res.data
}

export async function listVideoAipProjects(params: { limit?: number; workflow_type?: string; source_type?: string; source_ref_id?: number } = {}) {
  const res = await api.get('/api/copilot/video-aip/projects', { params })
  return res.data
}

export async function getVideoAipProject(projectId: number) {
  const res = await api.get(`/api/copilot/video-aip/projects/${projectId}`)
  return res.data
}

export async function updateVideoAipStep(projectId: number, stepId: number, params: { status: string; output?: Record<string, any>; error_message?: string }) {
  const res = await api.put(`/api/copilot/video-aip/projects/${projectId}/steps/${stepId}`, params)
  return res.data
}

export async function runVideoAipStep(projectId: number, stepId: number, params: Record<string, any> = {}) {
  const res = await api.post(`/api/copilot/video-aip/projects/${projectId}/steps/${stepId}/run`, params)
  return res.data
}

export async function runNextVideoAipStep(projectId: number) {
  const res = await api.post(`/api/copilot/video-aip/projects/${projectId}/run-next`)
  return res.data
}

export async function runAllVideoAipSteps(projectId: number) {
  const res = await api.post(`/api/copilot/video-aip/projects/${projectId}/run-all`)
  return res.data
}

export async function retryVideoAipStep(projectId: number, stepId: number, params: Record<string, any> = {}) {
  const res = await api.post(`/api/copilot/video-aip/projects/${projectId}/steps/${stepId}/retry`, params)
  return res.data
}
