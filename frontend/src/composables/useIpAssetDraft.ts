import type { IpSectionKey } from '../config/ipAssetTemplates'

export interface IpAssetDraftForm {
  name: string
  type: string
  industry: string
  targetAudience: string
  businessGoal: string
  mainPlatforms: string
  secondaryPlatforms: string
  tone: string
  visualStyle: string
  conversionPath: string
  forbiddenExpressions: string
}

export interface IpAssetDraftSnapshot {
  form: IpAssetDraftForm
  stage: string
  selectedTemplateKeys: Record<IpSectionKey, string>
  updatedAt: string
}

const IP_DRAFT_STORAGE_KEY = 'ip-case-asset-draft'

export function hasStoredIpAssetDraft() {
  try {
    const raw = window.sessionStorage.getItem(IP_DRAFT_STORAGE_KEY)
    if (!raw) return false
    const draft = JSON.parse(raw) as IpAssetDraftSnapshot
    return Object.values(draft.form || {}).some((value) => String(value || '').trim())
  } catch {
    return false
  }
}

export function persistIpAssetDraft(snapshot: IpAssetDraftSnapshot) {
  const hasContent = Object.values(snapshot.form).some((value) => String(value || '').trim())
  if (!hasContent) {
    window.sessionStorage.removeItem(IP_DRAFT_STORAGE_KEY)
    return
  }
  window.sessionStorage.setItem(IP_DRAFT_STORAGE_KEY, JSON.stringify(snapshot))
}

export function restoreIpAssetDraft(): IpAssetDraftSnapshot | null {
  try {
    const raw = window.sessionStorage.getItem(IP_DRAFT_STORAGE_KEY)
    if (!raw) return null
    return JSON.parse(raw) as IpAssetDraftSnapshot
  } catch {
    return null
  }
}

export function clearIpAssetDraft() {
  window.sessionStorage.removeItem(IP_DRAFT_STORAGE_KEY)
}
