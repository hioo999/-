import type {
  ApiResponse,
  AclEntry,
  AgentStatus,
  ActivationResult,
  AuditLog,
  AiAssistantFeedback,
  AiAssistantSetting,
  ChatMessage,
  ChatSession,
  CaseMember,
  CaseSpace,
  DirectoryPermission,
  EnterpriseOverview,
  EnterpriseProfile,
  ExternalOrgIntegration,
  KnowledgeBase,
  KnowledgeBaseGovernanceAudit,
  KnowledgeBaseMember,
  KnowledgeBaseReviewLog,
  KnowledgeBaseStats,
  KnowledgeBaseTree,
  FilePreview,
  LocalDataSource,
  LocalFile,
  LoginResult,
  ModelConfig,
  ModelConnectivityResult,
  NativePreviewStatus,
  OrganizationMember,
  OrganizationUnit,
  PermissionAction,
  PermissionCheckResult,
  ProcessingTask,
  RagAnswer,
  RunPendingTasksResult,
  ScanResult,
  SetupStatus,
  SyncQdrantResult,
  EffectivePermissions,
  ResourceType,
  WorkerRunOnceResult
} from '../types/api';
import { getToken } from './tokenStore';

const API_BASE = import.meta.env.VITE_AGENT_API_BASE ?? '';

async function readJsonBody<T>(response: Response, path: string): Promise<ApiResponse<T>> {
  const text = await response.text();
  if (!text.trim()) {
    throw new Error(`接口无响应：HTTP ${response.status} ${path}`);
  }
  try {
    return JSON.parse(text) as ApiResponse<T>;
  } catch {
    throw new Error(`接口返回非 JSON 内容：HTTP ${response.status} ${path}`);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(init.headers);
  headers.set('Content-Type', 'application/json');
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  } catch (error) {
    throw new Error(`接口连接失败：${(error as Error).message}`);
  }
  const body = await readJsonBody<T>(response, path);
  if (!response.ok || body.code !== 0) {
    throw new Error(body.message || `request failed: ${response.status}`);
  }
  return body.data;
}

async function requestBlob(path: string): Promise<{ blob: Blob; headers: Headers; response: Response }> {
  const token = getToken();
  const headers = new Headers();
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  const response = await fetch(`${API_BASE}${path}`, { headers });
  if (!response.ok) {
    let message = `request failed: ${response.status}`;
    try {
      const body = await readJsonBody<unknown>(response, path);
      message = body.message || message;
    } catch {
      // Ignore non-JSON error bodies.
    }
    throw new Error(message);
  }
  return { blob: await response.blob(), headers: response.headers, response };
}

export const agentClient = {
  setupStatus() {
    return request<SetupStatus>('/api/agent/setup/status');
  },
  setupAdmin(payload: { account: string; name: string; password: string }) {
    return request<LoginResult['user']>('/api/agent/setup/admin', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },
  login(account: string, password: string) {
    return request<LoginResult>('/api/agent/auth/login', {
      method: 'POST',
      body: JSON.stringify({ account, password })
    });
  },
  logout() {
    return request<{ logged_out: boolean }>('/api/agent/auth/logout', { method: 'POST' });
  },
  me() {
    return request<LoginResult['user']>('/api/agent/auth/me');
  },
  status() {
    return request<AgentStatus>('/api/agent/status');
  },
  dataSources() {
    return request<LocalDataSource[]>('/api/agent/data-sources');
  },
  knowledgeBases() {
    return request<KnowledgeBase[]>('/api/agent/knowledge-bases');
  },
  createKnowledgeBase(payload: { type: 'private' | 'team'; name: string; description?: string; ai_enabled?: boolean; knowledge_type?: KnowledgeBase['knowledge_type']; business_domain?: string; legal_domain?: string; jurisdiction?: string; client_id?: string; matter_id?: string; department_id?: string; project_team_id?: string; ethical_wall_enabled?: boolean; review_status?: KnowledgeBase['review_status']; confidentiality_level?: KnowledgeBase['confidentiality_level']; maintainer_id?: string; expires_at?: number | null; ai_usage_policy?: KnowledgeBase['ai_usage_policy']; citation_priority?: number; default_permission_policy?: string }) {
    return request<KnowledgeBase>('/api/agent/knowledge-bases', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },
  updateKnowledgeBase(knowledgeBaseId: string, payload: Partial<Pick<KnowledgeBase, 'name' | 'description' | 'ai_enabled' | 'default_permission_policy' | 'knowledge_type' | 'business_domain' | 'legal_domain' | 'jurisdiction' | 'client_id' | 'matter_id' | 'department_id' | 'project_team_id' | 'ethical_wall_enabled' | 'review_status' | 'confidentiality_level' | 'maintainer_id' | 'expires_at' | 'ai_usage_policy' | 'citation_priority'>>) {
    return request<KnowledgeBase>(`/api/agent/knowledge-bases/${knowledgeBaseId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload)
    });
  },
  deleteKnowledgeBase(knowledgeBaseId: string) {
    return request<{ id: string; deleted: boolean; status: string }>(`/api/agent/knowledge-bases/${knowledgeBaseId}`, { method: 'DELETE' });
  },
  reviewKnowledgeBase(knowledgeBaseId: string, payload: { action: 'submit_review' | 'publish' | 'reject' | 'mark_needs_update' | 'deprecate' | 'disable_ai' | 'enable_ai'; ai_usage_policy?: KnowledgeBase['ai_usage_policy']; comment?: string; reason?: string }) {
    return request<KnowledgeBase>(`/api/agent/knowledge-bases/${knowledgeBaseId}/review`, {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },
  knowledgeBaseReviewLogs(knowledgeBaseId: string) {
    return request<KnowledgeBaseReviewLog[]>(`/api/agent/knowledge-bases/${knowledgeBaseId}/review-logs`);
  },
  knowledgeBaseGovernanceAudit(knowledgeBaseId: string) {
    return request<KnowledgeBaseGovernanceAudit[]>(`/api/agent/knowledge-bases/${knowledgeBaseId}/governance-audit`);
  },
  archiveKnowledgeBase(knowledgeBaseId: string) {
    return request<{ id: string; status: string }>(`/api/agent/knowledge-bases/${knowledgeBaseId}/archive`, { method: 'POST' });
  },
  knowledgeBaseTree(knowledgeBaseId: string, options?: { includeDeleted?: boolean }) {
    const query = options?.includeDeleted ? '?include_deleted=true' : '';
    return request<KnowledgeBaseTree>(`/api/agent/knowledge-bases/${knowledgeBaseId}/tree${query}`);
  },
  knowledgeBaseStats(knowledgeBaseId: string) {
    return request<KnowledgeBaseStats>(`/api/agent/knowledge-bases/${knowledgeBaseId}/stats`);
  },
  knowledgeBaseMembers(knowledgeBaseId: string) {
    return request<KnowledgeBaseMember[]>(`/api/agent/knowledge-bases/${knowledgeBaseId}/members`);
  },
  grantKnowledgeBaseMember(knowledgeBaseId: string, payload: { principal_id: string; role_code: 'admin' | 'editor' | 'viewer' }) {
    return request<KnowledgeBaseMember>(`/api/agent/knowledge-bases/${knowledgeBaseId}/members`, {
      method: 'POST',
      body: JSON.stringify({ ...payload, principal_type: 'user' })
    });
  },
  revokeKnowledgeBaseMember(knowledgeBaseId: string, memberId: string) {
    return request<{ revoked: boolean; id: string }>(`/api/agent/knowledge-bases/${knowledgeBaseId}/members/${memberId}/revoke`, { method: 'POST' });
  },
  createFolder(payload: { knowledge_base_id: string; parent_id?: string | null; name: string }) {
    return request<KnowledgeBaseTree['folders'][number]>('/api/agent/folders', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },
  updateFolder(folderId: string, payload: { name?: string; parent_id?: string | null; sort_order?: number }) {
    return request<KnowledgeBaseTree['folders'][number]>(`/api/agent/folders/${folderId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload)
    });
  },
  deleteFolder(folderId: string) {
    return request<{ id: string; deleted: boolean; folder_count: number; knowledge_base_id: string }>(`/api/agent/folders/${folderId}`, { method: 'DELETE' });
  },
  restoreFolder(folderId: string) {
    return request<KnowledgeBaseTree['folders'][number]>(`/api/agent/folders/${folderId}/restore`, { method: 'POST' });
  },
  resourcePermissions(resourceType: ResourceType, resourceId: string) {
    return request<AclEntry[]>(`/api/agent/permissions/resource?resource_type=${encodeURIComponent(resourceType)}&resource_id=${encodeURIComponent(resourceId)}`);
  },
  effectivePermissions(resourceType: ResourceType, resourceId: string, userId?: string) {
    const query = new URLSearchParams({ resource_type: resourceType, resource_id: resourceId });
    if (userId) query.set('user_id', userId);
    return request<EffectivePermissions>(`/api/agent/permissions/effective?${query.toString()}`);
  },
  grantPermission(payload: { resource_type: ResourceType; resource_id: string; principal_id: string; action: PermissionAction; expires_at?: number | null }) {
    return request<AclEntry>('/api/agent/permissions/grant', {
      method: 'POST',
      body: JSON.stringify({ ...payload, principal_type: 'user' })
    });
  },
  denyPermission(payload: { resource_type: ResourceType; resource_id: string; principal_id: string; action: PermissionAction; expires_at?: number | null }) {
    return request<AclEntry>('/api/agent/permissions/deny', {
      method: 'POST',
      body: JSON.stringify({ ...payload, principal_type: 'user' })
    });
  },
  checkPermission(payload: { resource_type: ResourceType; resource_id: string; action: PermissionAction; user_id?: string }) {
    return request<PermissionCheckResult>('/api/agent/permissions/check', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },
  deletePermission(entryId: string) {
    return request<{ id: string; deleted: boolean }>(`/api/agent/permissions/${entryId}`, { method: 'DELETE' });
  },
  users() {
    return request<LoginResult['user'][]>('/api/agent/users');
  },
  createUser(payload: { account: string; name: string; role: string; password: string }) {
    return request<LoginResult['user']>('/api/agent/users', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },
  disableUser(userId: string) {
    return request<LoginResult['user']>(`/api/agent/users/${userId}/disable`, { method: 'POST' });
  },
  resetUserPassword(userId: string, password: string) {
    return request<LoginResult['user']>(`/api/agent/users/${userId}/reset-password`, {
      method: 'POST',
      body: JSON.stringify({ password })
    });
  },
  caseMembers(caseId?: string) {
    const query = caseId ? `?case_id=${encodeURIComponent(caseId)}` : '';
    return request<CaseMember[]>(`/api/agent/case-members${query}`);
  },
  grantCaseMember(payload: { case_id: string; user_id: string; role_code: string }) {
    return request<CaseMember>('/api/agent/case-members', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },
  revokeCaseMember(memberId: string) {
    return request<{ revoked: boolean; id: string }>(`/api/agent/case-members/${memberId}/revoke`, { method: 'POST' });
  },
  enterpriseOverview() {
    return request<EnterpriseOverview>('/api/agent/enterprise/overview');
  },
  enterpriseProfile() {
    return request<EnterpriseProfile>('/api/agent/enterprise/profile');
  },
  saveEnterpriseProfile(payload: { name: string; source_type: EnterpriseProfile['source_type'] }) {
    return request<EnterpriseProfile>('/api/agent/enterprise/profile', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },
  organizationUnits() {
    return request<OrganizationUnit[]>('/api/agent/organization/units');
  },
  createOrganizationUnit(payload: { name: string; unit_type: OrganizationUnit['unit_type']; parent_id?: string | null; sort_order?: number }) {
    return request<OrganizationUnit>('/api/agent/organization/units', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },
  organizationMembers() {
    return request<OrganizationMember[]>('/api/agent/organization/members');
  },
  assignOrganizationMember(payload: { user_id: string; unit_id?: string | null; position?: string }) {
    return request<OrganizationMember>('/api/agent/organization/members', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },
  externalOrgIntegrations() {
    return request<ExternalOrgIntegration[]>('/api/agent/external-org/integrations');
  },
  saveExternalOrgIntegration(payload: { provider: ExternalOrgIntegration['provider']; corp_id?: string; agent_id?: string; app_key?: string; app_id?: string; secret?: string; callback_url?: string; sync_enabled?: boolean }) {
    return request<ExternalOrgIntegration>('/api/agent/external-org/integrations', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },
  triggerExternalOrgSync(provider: ExternalOrgIntegration['provider']) {
    return request<{ provider: string; sync_status: string; last_sync_at: number }>(`/api/agent/external-org/integrations/${provider}/sync`, { method: 'POST' });
  },
  aiAssistantSetting() {
    return request<AiAssistantSetting>('/api/agent/ai-assistant/settings');
  },
  saveAiAssistantSetting(payload: Partial<AiAssistantSetting>) {
    return request<AiAssistantSetting>('/api/agent/ai-assistant/settings', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },
  aiAssistantFeedback() {
    return request<AiAssistantFeedback[]>('/api/agent/ai-assistant/feedback');
  },
  createAiAssistantFeedback(payload: { rating: AiAssistantFeedback['rating']; session_id?: string; message_id?: string; comment?: string; issue_label?: string }) {
    return request<AiAssistantFeedback>('/api/agent/ai-assistant/feedback', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },
  handleAiAssistantFeedback(feedbackId: string, payload: { status: AiAssistantFeedback['status']; resolution_comment?: string }) {
    return request<AiAssistantFeedback>(`/api/agent/ai-assistant/feedback/${feedbackId}/handle`, {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },
  activate(payload: { tenant_id: string; license_key_hash: string; agent_id?: string }) {
    return request<ActivationResult>('/api/agent/activate', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },
  reportHealth() {
    return request<unknown>('/api/agent/report-health', { method: 'POST' });
  },
  auditLogs() {
    return request<AuditLog[]>('/api/agent/audit-logs');
  },
  checkDirectory(path: string) {
    return request<DirectoryPermission>('/api/agent/data-sources/check-permission', {
      method: 'POST',
      body: JSON.stringify({ path })
    });
  },
  addDataSource(path: string) {
    return request<LocalDataSource>('/api/agent/data-sources', {
      method: 'POST',
      body: JSON.stringify({ path })
    });
  },
  scanDataSource(dataSourceId: string, caseId?: string, knowledgeBaseId?: string, folderId?: string) {
    return request<ScanResult>(`/api/agent/data-sources/${dataSourceId}/scan`, {
      method: 'POST',
      body: JSON.stringify({ case_id: caseId, knowledge_base_id: knowledgeBaseId, folder_id: folderId })
    });
  },
  tasks(caseId?: string) {
    const query = caseId ? `?case_id=${encodeURIComponent(caseId)}` : '';
    return request<ProcessingTask[]>(`/api/agent/tasks${query}`);
  },
  retryTask(taskId: string) {
    return request<unknown>(`/api/agent/tasks/${taskId}/retry`, { method: 'POST' });
  },
  runPendingTasks(limit = 20) {
    return request<RunPendingTasksResult>('/api/agent/tasks/run-pending', {
      method: 'POST',
      body: JSON.stringify({ limit })
    });
  },
  runWorkerOnce(batchSize = 20) {
    return request<WorkerRunOnceResult>('/api/agent/worker/run-once', {
      method: 'POST',
      body: JSON.stringify({ batch_size: batchSize })
    });
  },
  syncQdrantVectors(limit = 500, caseId?: string) {
    return request<SyncQdrantResult>('/api/agent/vector-store/sync-qdrant', {
      method: 'POST',
      body: JSON.stringify({ limit, case_id: caseId })
    });
  },
  cases() {
    return request<CaseSpace[]>('/api/agent/cases');
  },
  createCase(title: string) {
    return request<CaseSpace>('/api/agent/cases', {
      method: 'POST',
      body: JSON.stringify({ title })
    });
  },
  uploadFile(caseId: string, fileName: string, contentBase64: string, knowledgeBaseId?: string, folderId?: string) {
    return request<LocalFile>('/api/agent/files/upload', {
      method: 'POST',
      body: JSON.stringify({ case_id: caseId, knowledge_base_id: knowledgeBaseId, folder_id: folderId, file_name: fileName, content_base64: contentBase64 })
    });
  },
  uploadKnowledgeFile(knowledgeBaseId: string, fileName: string, contentBase64: string, folderId?: string) {
    return request<LocalFile>('/api/agent/files/upload', {
      method: 'POST',
      body: JSON.stringify({ knowledge_base_id: knowledgeBaseId, folder_id: folderId, file_name: fileName, content_base64: contentBase64 })
    });
  },
  files(caseId?: string) {
    const query = caseId ? `?case_id=${encodeURIComponent(caseId)}` : '';
    return request<LocalFile[]>(`/api/agent/files${query}`);
  },
  updateFile(fileId: string, payload: Partial<Pick<LocalFile, 'file_name' | 'folder_id' | 'review_status' | 'confidentiality_level' | 'maintainer_id' | 'expires_at' | 'ai_usage_policy' | 'ai_enabled'>> & { content_base64?: string }) {
    return request<LocalFile>(`/api/agent/files/${fileId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload)
    });
  },
  deleteFile(fileId: string) {
    return request<{ id: string; deleted: boolean }>(`/api/agent/files/${fileId}`, { method: 'DELETE' });
  },
  restoreFile(fileId: string) {
    return request<LocalFile>(`/api/agent/files/${fileId}/restore`, { method: 'POST' });
  },
  filePreview(fileId: string) {
    return request<FilePreview>(`/api/agent/files/${fileId}/preview`);
  },
  nativePreview(fileId: string) {
    return request<NativePreviewStatus>(`/api/agent/files/${fileId}/native-preview`);
  },
  runNativePreview(fileId: string) {
    return request<NativePreviewStatus>(`/api/agent/files/${fileId}/native-preview/run`, { method: 'POST' });
  },
  fileContent(fileId: string) {
    return requestBlob(`/api/agent/files/${fileId}/content`);
  },
  modelConfigs() {
    return request<ModelConfig[]>('/api/agent/model-configs');
  },
  saveModelConfig(payload: Record<string, string>) {
    return request<ModelConfig>('/api/agent/model-configs', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },
  testModelConfig(configId: string, mode: 'chat' | 'embedding') {
    return request<ModelConnectivityResult>(`/api/agent/model-configs/${configId}/test-${mode}`, { method: 'POST' });
  },
  ask(caseId: string, question: string) {
    return request<RagAnswer>('/api/agent/rag/query', {
      method: 'POST',
      body: JSON.stringify({ case_id: caseId, question })
    });
  },
  aiQuery(payload:
    | { context_scope: 'current_file'; file_id: string; question: string }
    | { context_scope: 'current_knowledge_base'; knowledge_base_id: string; question: string }
    | { context_scope: 'current_case'; case_id: string; question: string }
  ) {
    return request<RagAnswer>('/api/agent/ai/query', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },
  chats(caseId?: string) {
    const query = caseId ? `?case_id=${encodeURIComponent(caseId)}` : '';
    return request<ChatSession[]>(`/api/agent/chats${query}`);
  },
  chatMessages(sessionId: string) {
    return request<ChatMessage[]>(`/api/agent/chats/${sessionId}`);
  },
  askKnowledgeBase(knowledgeBaseId: string, question: string) {
    return request<RagAnswer>('/api/agent/rag/query', {
      method: 'POST',
      body: JSON.stringify({ knowledge_base_id: knowledgeBaseId, question })
    });
  }
};
