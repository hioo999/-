export type ApiResponse<T> = {
  code: number;
  message: string;
  data: T;
};

export type LocalUser = {
  id: string;
  account: string;
  name: string;
  role: string;
  status?: string;
  created_at?: number;
  last_login_at?: number | null;
};

export type LoginResult = {
  token: string;
  token_type: 'Bearer';
  expires_at: number;
  user: LocalUser;
};

export type SetupStatus = {
  setup_required: boolean;
  user_count: number;
  default_admin_password: boolean;
};

export type AgentStatus = {
  service: string;
  status: string;
  api: string;
  database: string;
  storage: string;
  task_queue: string;
  vector_store: string;
  embedding_vector_count?: number;
  qdrant_configured?: boolean;
  ocr_configured?: boolean;
  model_connectivity: string;
  model_provider?: string | null;
  chat_model?: string | null;
  embedding_model?: string | null;
};

export type CaseSpace = {
  id: string;
  title: string;
  cause_of_action?: string;
  stage?: string;
  status: string;
};

export type ProcessingTask = {
  id: string;
  file_id?: string;
  case_id?: string;
  task_type: string;
  status: string;
  error_code?: string | null;
  retry_count: number;
};

export type LocalDataSource = {
  id: string;
  type: string;
  path: string;
  status: string;
  permission_status: string;
  created_at: number;
};

export type DirectoryPermission = {
  path: string;
  exists: boolean;
  is_dir: boolean;
  readable: boolean;
  writable: boolean;
  permission_status: string;
};

export type LocalFile = {
  id: string;
  data_source_id?: string | null;
  case_id?: string | null;
  knowledge_base_id?: string | null;
  folder_id?: string | null;
  storage_mode?: string;
  file_name: string;
  file_path: string;
  file_ext?: string | null;
  file_size?: number | null;
  file_hash?: string | null;
  process_status: string;
  review_status?: KnowledgeBase['review_status'];
  confidentiality_level?: KnowledgeBase['confidentiality_level'];
  maintainer_id?: string | null;
  expires_at?: number | null;
  ai_usage_policy?: KnowledgeBase['ai_usage_policy'];
  ai_enabled?: boolean;
  is_high_sensitive?: boolean;
  sensitive_signal_types?: string[];
  task_id?: string;
  deduplicated?: boolean;
  deleted_at?: number | null;
};

export type KnowledgeBase = {
  id: string;
  type: 'private' | 'team' | 'case';
  name: string;
  description?: string | null;
  owner_type: string;
  owner_id: string;
  knowledge_type: 'general' | 'regulation' | 'case_law' | 'template' | 'clause' | 'pleading' | 'training' | 'project_review' | 'client_industry' | 'department_practice' | 'matter_workspace' | 'partner_selected' | 'ai_ready' | 'search_only';
  business_domain?: string | null;
  legal_domain?: string | null;
  jurisdiction?: string | null;
  client_id?: string | null;
  matter_id?: string | null;
  department_id?: string | null;
  project_team_id?: string | null;
  ethical_wall_enabled: boolean;
  review_status: 'draft' | 'pending_review' | 'published' | 'rejected' | 'archived' | 'deprecated' | 'needs_update' | 'ai_disabled';
  confidentiality_level: 'public' | 'internal' | 'confidential' | 'restricted';
  maintainer_id?: string | null;
  expires_at?: number | null;
  ai_usage_policy: 'allow_generation' | 'search_only' | 'disabled';
  citation_priority: number;
  ai_enabled: boolean;
  default_permission_policy: string;
  status: string;
  current_user_role?: string | null;
  created_by?: string | null;
  created_at: number;
  updated_at: number;
};

export type KnowledgeBaseMember = {
  id: string;
  knowledge_base_id: string;
  principal_type: string;
  principal_id: string;
  role_code: string;
  granted_by?: string | null;
  granted_at: number;
};

export type KnowledgeFolder = {
  id: string;
  knowledge_base_id: string;
  parent_id?: string | null;
  name: string;
  sort_order: number;
  permission_inherit: number;
  status: string;
  created_by?: string | null;
  created_at: number;
  updated_at: number;
  deleted_at?: number | null;
};

export type KnowledgeBaseTree = {
  knowledge_base: KnowledgeBase;
  folders: KnowledgeFolder[];
  files: LocalFile[];
};

export type KnowledgeBaseStats = {
  knowledge_base_id: string;
  file_count: number;
  folder_count: number;
  member_count: number;
  total_size: number;
};

export type KnowledgeBaseReviewLog = {
  id: string;
  knowledge_base_id: string;
  action: string;
  from_status: KnowledgeBase['review_status'];
  to_status: KnowledgeBase['review_status'];
  operator_id: string;
  comment?: string | null;
  created_at: number;
};

export type KnowledgeBaseGovernanceAudit = {
  id: string;
  knowledge_base_id: string;
  field_name: string;
  old_value?: string | null;
  new_value?: string | null;
  operator_id: string;
  created_at: number;
};

export type FilePreview = {
  file: LocalFile;
  source: 'chunks' | 'raw_file' | 'unavailable';
  status: string;
  text: string;
  chunks: Array<{
    chunk_id: string;
    chunk_index: number;
    text: string;
    page_number?: number | null;
    paragraph_ref?: string | null;
  }>;
  chunk_count: number;
  truncated: boolean;
  error?: string | null;
  watermark: {
    id: string;
    user_id: string;
    user_account: string;
    file_id: string;
    file_name: string;
    action: string;
    watermark_text: string;
    created_at: number;
  };
  high_risk_event?: {
    id: string;
    user_id: string;
    file_id: string;
    file_name: string;
    action: string;
    risk_reasons: string[];
    created_at: number;
  } | null;
};

export type NativePreviewStatus = {
  file_id: string;
  status: 'native_ready' | 'converting' | 'conversion_failed' | 'unsupported' | 'unavailable' | 'blocked';
  content_type?: string | null;
  task_id?: string | null;
  error?: string | null;
};

export type PermissionAction = 'view' | 'preview' | 'upload' | 'edit' | 'delete' | 'download' | 'ai_query' | 'grant' | 'audit_view';

export type ResourceType = 'knowledge_base' | 'folder' | 'file';

export type AclEntry = {
  id: string;
  resource_type: ResourceType;
  resource_id: string;
  principal_type: string;
  principal_id: string;
  action: PermissionAction;
  effect: 'allow' | 'deny';
  inherit: number;
  created_by?: string | null;
  created_at: number;
  expires_at?: number | null;
  is_expired?: boolean;
};

export type EffectivePermissions = {
  resource_type: ResourceType;
  resource_id: string;
  user_id: string;
  permissions: Record<PermissionAction, boolean>;
  boundary: {
    knowledge_base_id: string;
    user_id: string;
    client_id?: string | null;
    matter_id?: string | null;
    department_id?: string | null;
    project_team_id?: string | null;
    enabled_dimensions: Array<'client' | 'matter' | 'department' | 'project_team'>;
    ethical_wall_enabled: boolean;
    client_member?: boolean | null;
    matter_member?: boolean | null;
    department_member?: boolean | null;
    project_team_member?: boolean | null;
    allowed_by_boundary: boolean;
    reasons: string[];
  };
};

export type PermissionCheckResult = {
  allowed: boolean;
  user_id: string;
  action: PermissionAction;
};

export type ScanResult = {
  data_source_id: string;
  case_id?: string | null;
  knowledge_base_id?: string | null;
  folder_id?: string | null;
  discovered_count: number;
  added_count: number;
  duplicate_count: number;
  unsupported_count: number;
  enqueued_count: number;
  error_count: number;
  files: LocalFile[];
  errors: Array<{ path: string; message: string }>;
};

export type Citation = {
  case_id: string;
  knowledge_base_id?: string | null;
  file_id: string;
  file_name: string;
  chunk_id: string;
  chunk_index: number;
  page_number?: number | null;
  paragraph_ref?: string | null;
  quote_text: string;
  relevance_score: number;
  retrieval_mode?: string;
  governance_flags?: string[];
  knowledge_type?: KnowledgeBase['knowledge_type'] | null;
  knowledge_trust_level?: string | null;
  citation_priority?: number | null;
  file_review_status?: string | null;
  file_ai_usage_policy?: string | null;
  file_expires_at?: number | null;
  file_is_expired?: boolean;
  file_requires_maintenance?: boolean;
};

export type RagAnswer = {
  answer: string;
  structured_legal_answer?: LegalAnswerSection[];
  citations: Citation[];
  session_id: string;
  message_id?: string;
  insufficient_evidence: boolean;
  context_scope?: 'current_file' | 'current_knowledge_base' | 'current_case';
  model_used?: boolean;
  model_status?: string;
  model_error_code?: string | null;
  scenario?: string;
};

export type LegalAnswerSection = {
  title: '结论' | '依据' | '引用来源' | '适用前提' | '风险提示' | '不确定事项' | '建议下一步';
  content: string;
};

export type ChatSession = {
  id: string;
  case_id: string;
  user_id?: string | null;
  title?: string | null;
  save_mode: string;
  created_at: number;
};

export type ChatMessage = {
  id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  has_citations: number;
  citations?: Citation[];
  created_at: number;
};

export type RunPendingTasksResult = {
  requested_limit: number;
  picked_count: number;
  success_count: number;
  failed_count: number;
  tasks: Array<{ task_id: string; file_id: string; status: string; chunks?: number; error?: string }>;
};

export type SyncQdrantResult = {
  qdrant_configured: boolean;
  collection?: string;
  picked_count: number;
  synced_count: number;
  updated_ref_count: number;
  status: string;
};

export type CaseMember = {
  id: string;
  case_id: string;
  case_title: string;
  user_id: string;
  account: string;
  name: string;
  user_status: string;
  role_code: string;
  granted_by?: string | null;
  granted_at: number;
};

export type AuditLog = {
  id: string;
  user_id?: string | null;
  action: string;
  target_type: string;
  target_id?: string | null;
  ip_address?: string | null;
  user_agent?: string | null;
  created_at: number;
};

export type ActivationResult = {
  agent_id: string;
  platform_result: unknown;
};

export type WorkerRunOnceResult = {
  status: string;
  processed_count: number;
  pending: RunPendingTasksResult;
  retries: RunPendingTasksResult;
  qdrant_sync: SyncQdrantResult;
};

export type ModelConfig = {
  id: string;
  provider: string;
  base_url: string;
  chat_model: string;
  embedding_model: string;
  status: string;
  api_key_configured: boolean;
  api_key_masked: string;
};

export type ModelConnectivityResult = {
  config_id: string;
  mode: 'chat' | 'embedding';
  status: 'success' | 'failed';
  provider: string;
  base_url: string;
  model: string;
  api_key_configured: boolean;
  latency_ms: number;
  error_code?: string | null;
  message: string;
};

export type EnterpriseProfile = {
  id: string;
  name: string;
  source_type: 'manual' | 'wecom' | 'dingtalk' | 'feishu' | 'mixed';
  status: string;
  created_at: number;
  updated_at: number;
};

export type EnterpriseOverview = {
  enterprise: EnterpriseProfile;
  member_count: number;
  admin_count: number;
  department_count: number;
  external_collaborator_count: number;
  active_knowledge_base_count: number;
  file_count: number;
  folder_count: number;
  last_sync_at?: number | null;
  stats_until: number;
  knowledge_review_status_counts: Record<string, number>;
  knowledge_type_counts: Record<string, number>;
  knowledge_ai_disabled_count: number;
  knowledge_search_only_count: number;
  knowledge_expired_count: number;
  file_review_status_counts: Record<string, number>;
  file_ai_disabled_count: number;
  high_sensitive_file_count: number;
  high_risk_access_count: number;
  high_risk_access_action_counts: Record<string, number>;
  permission_anomaly_count: number;
  permission_anomaly_type_counts: Record<string, number>;
  permission_anomaly_samples: Array<Record<string, string | number | null>>;
  temporary_acl_active_count: number;
  temporary_acl_expired_count: number;
  file_search_only_count: number;
  file_expired_count: number;
  ai_feedback_total_count: number;
  ai_feedback_negative_count: number;
  ai_feedback_open_count: number;
  ai_feedback_resolved_count: number;
  ai_feedback_ignored_count: number;
  ai_feedback_issue_counts: Record<string, number>;
  ai_feedback_citation_missing_count: number;
  ai_feedback_insufficient_evidence_count: number;
  ai_feedback_answer_inaccurate_count?: number;
  ai_feedback_permission_anomaly_count?: number;
  ai_question_count: number;
  ai_insufficient_evidence_count: number;
  ai_insufficient_evidence_rate: number;
  knowledge_trust_level_counts: Record<string, number>;
  low_usage_knowledge_top: Array<{ id: string; name: string; knowledge_type: KnowledgeBase['knowledge_type']; maintainer_id?: string | null; ai_question_count: number }>;
  high_risk_file_access_top: Array<{ file_id: string; file_name: string; access_count: number; last_access_at: number }>;
  ai_user_top: Array<{ user_id: string; user_name: string; ai_question_count: number }>;
  estimated_time_saved_minutes: number;
  knowledge_quality_top: Array<{
    id: string;
    name: string;
    knowledge_type: KnowledgeBase['knowledge_type'];
    review_status: KnowledgeBase['review_status'];
    maintainer_id?: string | null;
    file_count: number;
    expired_file_count: number;
    high_sensitive_file_count: number;
    ai_disabled_file_count: number;
    ai_question_count: number;
    insufficient_evidence_count: number;
    insufficient_evidence_rate: number;
    negative_feedback_count: number;
  }>;
  knowledge_contributor_top: Array<{
    maintainer_id: string;
    maintainer_name: string;
    knowledge_base_count: number;
    file_count: number;
    publish_ready_count: number;
    expired_knowledge_base_count: number;
  }>;
};

export type OrganizationUnit = {
  id: string;
  enterprise_id: string;
  parent_id?: string | null;
  name: string;
  unit_type: 'enterprise' | 'department' | 'team' | 'practice_group' | 'client' | 'matter' | 'project_team';
  source_type: string;
  external_id?: string | null;
  sort_order: number;
  status: string;
  created_at: number;
  updated_at: number;
};

export type OrganizationMember = {
  id: string;
  enterprise_id: string;
  unit_id?: string | null;
  user_id: string;
  position?: string | null;
  source_type: string;
  external_user_id?: string | null;
  status: string;
  joined_at: number;
  account: string;
  name: string;
  role: string;
  user_status: string;
  unit_name?: string | null;
};

export type ExternalOrgIntegration = {
  id: string;
  enterprise_id: string;
  provider: 'wecom' | 'dingtalk' | 'feishu';
  corp_id?: string | null;
  agent_id?: string | null;
  app_key?: string | null;
  app_id?: string | null;
  callback_url?: string | null;
  sync_enabled: boolean;
  last_sync_at?: number | null;
  sync_status: string;
  secret_configured: boolean;
  created_at: number;
  updated_at: number;
};

export type AiAssistantSetting = {
  id?: string | null;
  scope_type: 'enterprise' | 'department' | 'knowledge_base' | 'user';
  scope_id: string;
  name: string;
  system_prompt?: string | null;
  enabled: boolean;
  allowed_knowledge_base_ids: string[];
  updated_by?: string | null;
  updated_at?: number | null;
};

export type AiAssistantFeedback = {
  id: string;
  session_id?: string | null;
  message_id?: string | null;
  user_id?: string | null;
  rating: 'up' | 'down' | 'neutral';
  comment?: string | null;
  issue_label?: string | null;
  status: 'open' | 'resolved' | 'ignored';
  handler_id?: string | null;
  handled_at?: number | null;
  resolution_comment?: string | null;
  created_at: number;
};
