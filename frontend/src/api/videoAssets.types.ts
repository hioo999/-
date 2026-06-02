export interface VideoAssetAnalysisItem {
  filename: string
  path: string
  type: 'image' | 'video' | 'unknown'
  description: string
}
