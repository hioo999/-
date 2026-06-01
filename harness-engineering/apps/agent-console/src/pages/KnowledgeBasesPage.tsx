import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { Alert, Button, Card, Empty, Form, Input, Modal, Popconfirm, Select, Space, Table, Tag, Tree, Typography, message } from 'antd';
import { agentClient } from '../services/agentClient';
import type { AiAssistantFeedback, EnterpriseOverview, FilePreview, KnowledgeBase, KnowledgeBaseGovernanceAudit, KnowledgeBaseReviewLog, KnowledgeBaseTree, KnowledgeFolder, LocalFile, LocalUser, NativePreviewStatus } from '../types/api';
import { KnowledgeBaseChatPanel } from '../components/KnowledgeBaseChatPanel';

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const value = String(reader.result ?? '');
      resolve(value.includes(',') ? value.split(',')[1] : value);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function textToBase64(value: string) {
  const bytes = new TextEncoder().encode(value);
  let binary = '';
  bytes.forEach((byte) => {
    binary += String.fromCharCode(byte);
  });
  return btoa(binary);
}

const typeLabels: Record<KnowledgeBase['type'], string> = {
  private: '个人知识库',
  team: '共享知识库',
  case: '归档知识库'
};

const knowledgeTypeOptions: Array<{ label: string; value: KnowledgeBase['knowledge_type'] }> = [
  { label: '通用知识', value: 'general' },
  { label: '法规库', value: 'regulation' },
  { label: '案例库', value: 'case_law' },
  { label: '模板库', value: 'template' },
  { label: '条款库', value: 'clause' },
  { label: '文书库', value: 'pleading' },
  { label: '培训库', value: 'training' },
  { label: '复盘库', value: 'project_review' },
  { label: '客户行业库', value: 'client_industry' },
  { label: '部门专业库', value: 'department_practice' },
  { label: '案件专属库', value: 'matter_workspace' },
  { label: '精选库', value: 'partner_selected' },
  { label: 'AI 可用知识库', value: 'ai_ready' },
  { label: '仅检索库（兼容类型）', value: 'search_only' }
];

const knowledgeTypeLabels: Record<string, string> = Object.fromEntries(knowledgeTypeOptions.map((item) => [item.value, item.label]));

const reviewStatusOptions: Array<{ label: string; value: KnowledgeBase['review_status'] }> = [
  { label: '草稿', value: 'draft' },
  { label: '待审核', value: 'pending_review' },
  { label: '已发布', value: 'published' },
  { label: '已退回', value: 'rejected' },
  { label: '已归档', value: 'archived' },
  { label: '已废止', value: 'deprecated' },
  { label: '需更新', value: 'needs_update' },
  { label: '禁止 AI 使用', value: 'ai_disabled' }
];

const reviewStatusLabels: Record<string, string> = Object.fromEntries(reviewStatusOptions.map((item) => [item.value, item.label]));

const confidentialityOptions: Array<{ label: string; value: KnowledgeBase['confidentiality_level'] }> = [
  { label: '公开', value: 'public' },
  { label: '内部', value: 'internal' },
  { label: '保密', value: 'confidential' },
  { label: '高敏', value: 'restricted' }
];

const confidentialityLabels: Record<string, string> = Object.fromEntries(confidentialityOptions.map((item) => [item.value, item.label]));

const aiUsagePolicyOptions: Array<{ label: string; value: KnowledgeBase['ai_usage_policy'] }> = [
  { label: '允许检索与生成', value: 'allow_generation' },
  { label: '仅检索不可生成', value: 'search_only' },
  { label: '禁止 AI 使用', value: 'disabled' }
];

const aiUsagePolicyLabels: Record<string, string> = Object.fromEntries(aiUsagePolicyOptions.map((item) => [item.value, item.label]));

const feedbackIssueLabels: Record<string, string> = {
  citation_missing: '引用缺失',
  answer_inaccurate: '答案不准确',
  insufficient_evidence: '证据不足',
  permission_anomaly: '权限异常',
  answer_incomplete: '回答不完整',
  missed_question: '没有回答问题',
  other: '其他',
  knowledge_base_chat: '知识库问答'
};

const feedbackStatusLabels: Record<AiAssistantFeedback['status'], string> = {
  open: '待处理',
  resolved: '已解决',
  ignored: '已忽略'
};

const governanceFieldLabels: Record<string, string> = {
  knowledge_type: '知识类型',
  business_domain: '业务领域',
  legal_domain: '法律领域',
  jurisdiction: '管辖地',
  client_id: '客户',
  matter_id: '案件/事项',
  department_id: '部门',
  project_team_id: '项目组',
  ethical_wall_enabled: '客户墙',
  review_status: '审核状态',
  confidentiality_level: '保密等级',
  maintainer_id: '维护人',
  expires_at: '有效期',
  ai_usage_policy: 'AI 使用规则',
  citation_priority: '引用优先级',
  ai_enabled: 'AI 开关',
  default_permission_policy: '默认权限策略'
};

const highImpactKnowledgeTypes = new Set<KnowledgeBase['knowledge_type']>(['template', 'clause', 'pleading']);

const reviewActionLabels = {
  submit_review: '提交审核',
  publish: '发布',
  reject: '退回',
  mark_needs_update: '标记需更新',
  deprecate: '废止',
  disable_ai: '禁止 AI',
  enable_ai: '启用 AI'
} as const;

type ReviewAction = keyof typeof reviewActionLabels;

function formatTime(value?: number | null) {
  return value ? new Date(value * 1000).toLocaleString() : '-';
}

function formatDateInput(value?: number | null) {
  if (!value) return undefined;
  return new Date(value * 1000).toISOString().slice(0, 10);
}

function normalizeExpiresAt(value?: string | number | null) {
  if (value === '' || value == null) return null;
  if (typeof value === 'number') return value;
  const trimmed = value.trim();
  if (!trimmed) return null;
  if (/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) {
    return Math.floor(new Date(`${trimmed}T23:59:59`).getTime() / 1000);
  }
  const numeric = Number(trimmed);
  return Number.isFinite(numeric) ? numeric : null;
}

function formatFileSize(value?: number | null) {
  if (!value) return '-';
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

function publishReadinessGaps(knowledgeBase?: KnowledgeBase) {
  if (!knowledgeBase || !highImpactKnowledgeTypes.has(knowledgeBase.knowledge_type)) return [];
  const gaps = [];
  if (!knowledgeBase.maintainer_id) gaps.push('维护人');
  if (!knowledgeBase.citation_priority || knowledgeBase.citation_priority <= 0) gaps.push('引用优先级');
  if (!knowledgeBase.expires_at) gaps.push('有效期');
  return gaps;
}

const privateKnowledgeBaseOrder = ['AI资料', 'AI知识库', '战略思维', '读书学习'];
const teamKnowledgeBaseOrder = ['开发', '工具演练', '公众号资料', '教学课程', '海鸥知识库-实用提示词'];

const defaultKnowledgeBaseStructure: Array<{ type: 'private' | 'team'; name: string; description: string; knowledge_type: KnowledgeBase['knowledge_type']; review_status: KnowledgeBase['review_status']; confidentiality_level: KnowledgeBase['confidentiality_level']; ai_usage_policy: KnowledgeBase['ai_usage_policy'] }> = [
  { type: 'private', name: 'AI资料', description: '个人沉淀的 AI 资料、模型说明、工具文档和研究素材', knowledge_type: 'ai_ready', review_status: 'published', confidentiality_level: 'internal', ai_usage_policy: 'allow_generation' },
  { type: 'private', name: 'AI知识库', description: '个人可复用的 AI 知识、提示词、案例和操作方法', knowledge_type: 'ai_ready', review_status: 'published', confidentiality_level: 'internal', ai_usage_policy: 'allow_generation' },
  { type: 'private', name: '战略思维', description: '战略、商业、管理和长期判断相关资料', knowledge_type: 'general', review_status: 'published', confidentiality_level: 'internal', ai_usage_policy: 'allow_generation' },
  { type: 'private', name: '读书学习', description: '读书笔记、课程学习、摘录和复盘内容', knowledge_type: 'training', review_status: 'published', confidentiality_level: 'internal', ai_usage_policy: 'allow_generation' },
  { type: 'team', name: '开发', description: '团队开发资料、工程规范、代码实践和技术文档', knowledge_type: 'department_practice', review_status: 'published', confidentiality_level: 'internal', ai_usage_policy: 'allow_generation' },
  { type: 'team', name: '工具演练', description: '工具试用记录、操作步骤、评测结果和演练资料', knowledge_type: 'training', review_status: 'published', confidentiality_level: 'internal', ai_usage_policy: 'allow_generation' },
  { type: 'team', name: '公众号资料', description: '公众号选题、素材、文章资料和发布参考', knowledge_type: 'general', review_status: 'published', confidentiality_level: 'internal', ai_usage_policy: 'allow_generation' },
  { type: 'team', name: '教学课程', description: '课程大纲、教学材料、训练营和知识产品资料', knowledge_type: 'training', review_status: 'published', confidentiality_level: 'internal', ai_usage_policy: 'allow_generation' },
  { type: 'team', name: '海鸥知识库-实用提示词', description: '团队共享的实用提示词、问答范式和 AI 操作模板', knowledge_type: 'ai_ready', review_status: 'published', confidentiality_level: 'internal', ai_usage_policy: 'search_only' }
];

function orderedKnowledgeBases(items: KnowledgeBase[], type: KnowledgeBase['type'], order: string[]) {
  const rank = new Map(order.map((name, index) => [name, index]));
  return items
    .filter((item) => item.type === type)
    .sort((first, second) => {
      const firstRank = rank.get(first.name) ?? Number.MAX_SAFE_INTEGER;
      const secondRank = rank.get(second.name) ?? Number.MAX_SAFE_INTEGER;
      if (firstRank !== secondRank) return firstRank - secondRank;
      return first.name.localeCompare(second.name, 'zh-Hans-CN');
    });
}

type SidebarNodeMeta =
  | { type: 'root' }
  | { type: 'category'; knowledgeBaseType: KnowledgeBase['type'] }
  | { type: 'knowledge-base'; knowledgeBaseId: string }
  | { type: 'folder'; knowledgeBaseId: string; folderId: string }
  | { type: 'file'; knowledgeBaseId: string; fileId: string; folderId?: string | null };

type KnowledgeTreeNode = {
  key: string;
  title: ReactNode;
  children?: KnowledgeTreeNode[];
  disabled?: boolean;
  selectable?: boolean;
  isLeaf?: boolean;
  meta?: SidebarNodeMeta;
};

const rootKey = 'root:knowledge';
const categoryKey = (type: KnowledgeBase['type']) => `category:${type}`;
const knowledgeBaseKey = (id: string) => `kb:${id}`;
const folderKey = (id: string) => `folder:${id}`;
const fileKey = (id: string) => `file:${id}`;

function sortByOrderAndName<T extends { sort_order?: number; name?: string; file_name?: string }>(items: T[]) {
  return [...items].sort((first, second) => {
    const orderDiff = (first.sort_order ?? 0) - (second.sort_order ?? 0);
    if (orderDiff !== 0) return orderDiff;
    return (first.name ?? first.file_name ?? '').localeCompare(second.name ?? second.file_name ?? '', 'zh-Hans-CN');
  });
}

function buildFileNode(file: LocalFile, knowledgeBaseId: string): KnowledgeTreeNode {
  return {
    key: fileKey(file.id),
    title: file.file_name,
    isLeaf: true,
    meta: { type: 'file', knowledgeBaseId, fileId: file.id, folderId: file.folder_id }
  };
}

function buildFolderNodes(folders: KnowledgeFolder[], files: LocalFile[], knowledgeBaseId: string, parentId: string | null): KnowledgeTreeNode[] {
  const childFolders = sortByOrderAndName(folders.filter((folder) => (folder.parent_id ?? null) === parentId));
  const childFiles = sortByOrderAndName(files.filter((file) => (file.folder_id ?? null) === parentId));

  return [
    ...childFolders.map((folder) => ({
      key: folderKey(folder.id),
      title: folder.name,
      meta: { type: 'folder' as const, knowledgeBaseId, folderId: folder.id },
      children: buildFolderNodes(folders, files, knowledgeBaseId, folder.id)
    })),
    ...childFiles.map((file) => buildFileNode(file, knowledgeBaseId))
  ];
}

function findMeta(nodes: KnowledgeTreeNode[], key?: string): SidebarNodeMeta | undefined {
  if (!key) return undefined;
  for (const node of nodes) {
    if (node.key === key) return node.meta;
    const child = findMeta(node.children ?? [], key);
    if (child) return child;
  }
  return undefined;
}

function findFolder(tree: KnowledgeBaseTree | undefined, folderId?: string | null) {
  if (!folderId) return undefined;
  return tree?.folders.find((folder) => folder.id === folderId);
}

function findFile(tree: KnowledgeBaseTree | undefined, fileId?: string) {
  if (!fileId) return undefined;
  return tree?.files.find((item) => item.id === fileId);
}

export function KnowledgeBasesPage({
  initialKnowledgeBaseId,
  onKnowledgeBasesChanged,
  onSelectKnowledgeBase
}: {
  initialKnowledgeBaseId?: string;
  onKnowledgeBasesChanged?: () => Promise<unknown>;
  onSelectKnowledgeBase?: (knowledgeBaseId: string | undefined) => void;
}) {
  const [knowledgeBaseForm] = Form.useForm();
  const [knowledgeBaseSettingsForm] = Form.useForm();
  const [quickCreateForm] = Form.useForm();
  const [folderForm] = Form.useForm();
  const [folderEditForm] = Form.useForm();
  const [fileEditForm] = Form.useForm();
  const [fileMoveForm] = Form.useForm();
  const [fileGovernanceForm] = Form.useForm();
  const [textFileForm] = Form.useForm();
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [users, setUsers] = useState<LocalUser[]>([]);
  const [selectedId, setSelectedId] = useState<string>();
  const [selectedKey, setSelectedKey] = useState(categoryKey('private'));
  const [treesByKnowledgeBaseId, setTreesByKnowledgeBaseId] = useState<Record<string, KnowledgeBaseTree>>({});
  const [trashTreesByKnowledgeBaseId, setTrashTreesByKnowledgeBaseId] = useState<Record<string, KnowledgeBaseTree>>({});
  const [file, setFile] = useState<File | null>(null);
  const [fileInputVersion, setFileInputVersion] = useState(0);
  const [loading, setLoading] = useState(false);
  const [trashLoading, setTrashLoading] = useState(false);
  const [keyword, setKeyword] = useState('');
  const [typeFilter, setTypeFilter] = useState<KnowledgeBase['type'] | 'all'>('all');
  const [knowledgeTypeFilter, setKnowledgeTypeFilter] = useState<KnowledgeBase['knowledge_type'] | 'all'>('all');
  const [reviewStatusFilter, setReviewStatusFilter] = useState<KnowledgeBase['review_status'] | 'all'>('all');
  const [aiPolicyFilter, setAiPolicyFilter] = useState<KnowledgeBase['ai_usage_policy'] | 'all'>('all');
  const [quickCreateType, setQuickCreateType] = useState<'private' | 'team'>();
  const [filePreview, setFilePreview] = useState<FilePreview>();
  const [filePreviewLoading, setFilePreviewLoading] = useState(false);
  const [filePreviewError, setFilePreviewError] = useState<string>();
  const [contentUrl, setContentUrl] = useState<string>();
  const [contentType, setContentType] = useState<string>();
  const [contentLoading, setContentLoading] = useState(false);
  const [contentError, setContentError] = useState<string>();
  const [contentWatermark, setContentWatermark] = useState<string>();
  const [nativePreviewStatus, setNativePreviewStatus] = useState<NativePreviewStatus>();
  const [nativePreviewActionLoading, setNativePreviewActionLoading] = useState(false);
  const [nativePreviewRefreshVersion, setNativePreviewRefreshVersion] = useState(0);
  const [reviewLogs, setReviewLogs] = useState<KnowledgeBaseReviewLog[]>([]);
  const [reviewLogsLoading, setReviewLogsLoading] = useState(false);
  const [governanceAudit, setGovernanceAudit] = useState<KnowledgeBaseGovernanceAudit[]>([]);
  const [governanceAuditLoading, setGovernanceAuditLoading] = useState(false);
  const [reviewActionLoading, setReviewActionLoading] = useState<ReviewAction>();
  const [enterpriseOverview, setEnterpriseOverview] = useState<EnterpriseOverview>();
  const [aiFeedbacks, setAiFeedbacks] = useState<AiAssistantFeedback[]>([]);
  const [qualityLoading, setQualityLoading] = useState(false);

  const userOptions = users.filter((user) => user.status !== 'disabled').map((user) => ({ label: `${user.name}（${user.account}）`, value: user.id }));

  const renderGovernanceAuditValue = (fieldName: string, value?: string | null) => {
    if (value == null || value === '') return '-';
    if (fieldName === 'knowledge_type') return knowledgeTypeLabels[value] ?? value;
    if (fieldName === 'review_status') return reviewStatusLabels[value] ?? value;
    if (fieldName === 'confidentiality_level') return confidentialityLabels[value] ?? value;
    if (fieldName === 'ai_usage_policy') return aiUsagePolicyLabels[value] ?? value;
    if (fieldName === 'maintainer_id' || fieldName === 'operator_id') return users.find((user) => user.id === value)?.name ?? value;
    if (fieldName === 'ai_enabled' || fieldName === 'ethical_wall_enabled') return value === 'true' || value === '1' ? '启用' : '禁用';
    if (fieldName === 'expires_at') return formatTime(Number(value));
    return value;
  };

  const loadKnowledgeBases = async () => {
    const next = await agentClient.knowledgeBases();
    setKnowledgeBases(next);
    setSelectedId((current) => current ?? (initialKnowledgeBaseId && next.some((item) => item.id === initialKnowledgeBaseId) ? initialKnowledgeBaseId : next[0]?.id));
    setSelectedKey((current) => current || (initialKnowledgeBaseId && next.some((item) => item.id === initialKnowledgeBaseId) ? knowledgeBaseKey(initialKnowledgeBaseId) : next[0] ? knowledgeBaseKey(next[0].id) : categoryKey('private')));
    return next;
  };

  const loadTree = async (knowledgeBaseId: string) => {
    const nextTree = await agentClient.knowledgeBaseTree(knowledgeBaseId);
    setTreesByKnowledgeBaseId((current) => ({ ...current, [knowledgeBaseId]: nextTree }));
    return nextTree;
  };

  const loadTrashTree = async (knowledgeBaseId: string) => {
    const nextTree = await agentClient.knowledgeBaseTree(knowledgeBaseId, { includeDeleted: true });
    setTrashTreesByKnowledgeBaseId((current) => ({ ...current, [knowledgeBaseId]: nextTree }));
    return nextTree;
  };

  const loadUsers = async () => {
    const nextUsers = await agentClient.users();
    setUsers(nextUsers);
    return nextUsers;
  };

  const loadQualityFeedback = async () => {
    setQualityLoading(true);
    try {
      const [overview, feedbacks] = await Promise.all([agentClient.enterpriseOverview(), agentClient.aiAssistantFeedback()]);
      setEnterpriseOverview(overview);
      setAiFeedbacks(feedbacks);
      return { overview, feedbacks };
    } finally {
      setQualityLoading(false);
    }
  };

  const loadReviewLogs = async (knowledgeBaseId: string) => {
    setReviewLogsLoading(true);
    try {
      const nextLogs = await agentClient.knowledgeBaseReviewLogs(knowledgeBaseId);
      setReviewLogs(nextLogs);
      return nextLogs;
    } finally {
      setReviewLogsLoading(false);
    }
  };

  const loadGovernanceAudit = async (knowledgeBaseId: string) => {
    setGovernanceAuditLoading(true);
    try {
      const nextAudit = await agentClient.knowledgeBaseGovernanceAudit(knowledgeBaseId);
      setGovernanceAudit(nextAudit);
      return nextAudit;
    } finally {
      setGovernanceAuditLoading(false);
    }
  };

  const runSelectedNativePreview = async () => {
    if (!selectedFile) return;
    setNativePreviewActionLoading(true);
    setContentError(undefined);
    try {
      const status = await agentClient.runNativePreview(selectedFile.id);
      setNativePreviewStatus(status);
      setNativePreviewRefreshVersion((current) => current + 1);
      if (status.status === 'native_ready') {
        message.success('Office 版式预览已生成');
      } else if (status.status === 'conversion_failed') {
        message.warning(status.error || 'Office 版式预览转换失败');
      } else if (status.status === 'converting') {
        message.info('Office 版式预览任务已排队');
      }
    } catch (error) {
      message.error((error as Error).message || 'Office 版式预览任务执行失败');
    } finally {
      setNativePreviewActionLoading(false);
    }
  };

  useEffect(() => {
    loadKnowledgeBases().catch((error) => message.error(error.message));
    loadUsers().catch((error) => message.error(error.message));
    loadQualityFeedback().catch((error) => message.warning(error.message || '质量反馈统计加载失败'));
  }, []);

  useEffect(() => {
    if (!initialKnowledgeBaseId || !knowledgeBases.some((item) => item.id === initialKnowledgeBaseId)) return;
    setSelectedId(initialKnowledgeBaseId);
    setSelectedKey(knowledgeBaseKey(initialKnowledgeBaseId));
  }, [initialKnowledgeBaseId, knowledgeBases]);

  useEffect(() => {
    if (!selectedId) return;
    loadTree(selectedId).catch((error) => message.error(error.message));
  }, [selectedId]);

  const buildKnowledgeBaseNode = (item: KnowledgeBase): KnowledgeTreeNode => {
    const tree = treesByKnowledgeBaseId[item.id];
    const children = tree
      ? buildFolderNodes(tree.folders, tree.files, item.id, null)
      : [{ key: `hint:${item.id}`, title: '选择后加载目录和文件', disabled: true, selectable: false }];

    return {
      key: knowledgeBaseKey(item.id),
      title: item.name,
      meta: { type: 'knowledge-base', knowledgeBaseId: item.id },
      children
    };
  };

  const createRequiredKnowledgeBases = async () => {
    setLoading(true);
    try {
      const existing = new Set(knowledgeBases.map((item) => `${item.type}:${item.name}`));
      let createdCount = 0;
      for (const item of defaultKnowledgeBaseStructure) {
        if (existing.has(`${item.type}:${item.name}`)) continue;
        const created = await agentClient.createKnowledgeBase(item);
        existing.add(`${created.type}:${created.name}`);
        createdCount += 1;
      }
      const next = await loadKnowledgeBases();
      await onKnowledgeBasesChanged?.();
      const firstRequired = next.find((item) => item.type === 'private' && item.name === privateKnowledgeBaseOrder[0]) ?? next[0];
      if (firstRequired) {
        selectKnowledgeBase(firstRequired.id, knowledgeBaseKey(firstRequired.id));
        await loadTree(firstRequired.id);
      }
      message.success(createdCount ? `已补齐 ${createdCount} 个指定知识库` : '指定知识库结构已存在');
    } finally {
      setLoading(false);
    }
  };

  const openQuickCreate = (type: 'private' | 'team') => {
    setQuickCreateType(type);
    setSelectedKey(categoryKey(type));
    quickCreateForm.resetFields();
  };

  const filteredKnowledgeBases = knowledgeBases.filter((item) => {
    const normalizedKeyword = keyword.trim().toLowerCase();
    const matchesKeyword = !normalizedKeyword
      || item.name.toLowerCase().includes(normalizedKeyword)
      || String(item.description ?? '').toLowerCase().includes(normalizedKeyword);
    return matchesKeyword
      && (typeFilter === 'all' || item.type === typeFilter)
      && (knowledgeTypeFilter === 'all' || item.knowledge_type === knowledgeTypeFilter)
      && (reviewStatusFilter === 'all' || item.review_status === reviewStatusFilter)
      && (aiPolicyFilter === 'all' || item.ai_usage_policy === aiPolicyFilter);
  });

  const buildCategoryNode = (type: KnowledgeBase['type'], title: string): KnowledgeTreeNode => {
    const items = orderedKnowledgeBases(filteredKnowledgeBases, type, type === 'private' ? privateKnowledgeBaseOrder : teamKnowledgeBaseOrder);
    const titleNode = type === 'private' || type === 'team' ? (
      <span className="knowledge-category-title">
        <span>{title}</span>
        <Button
          aria-label={`新建${title}`}
          className="knowledge-category-add"
          type="text"
          size="small"
          onClick={(event) => {
            event.stopPropagation();
            openQuickCreate(type);
          }}
        >
          +
        </Button>
      </span>
    ) : `${title}（${items.length}）`;

    return {
      key: categoryKey(type),
      title: titleNode,
      meta: { type: 'category', knowledgeBaseType: type },
      children: items.map(buildKnowledgeBaseNode)
    };
  };

  const categoryNodes = [
    buildCategoryNode('private', '个人知识库'),
    buildCategoryNode('team', '共享知识库')
  ].filter((node) => typeFilter === 'all' || node.meta?.type !== 'category' || node.meta.knowledgeBaseType === typeFilter);

  const treeData: KnowledgeTreeNode[] = [
    {
      key: rootKey,
      title: `知识库（${filteredKnowledgeBases.length}/${knowledgeBases.length}）`,
      meta: { type: 'root' },
      children: categoryNodes
    }
  ];
  const selectedMeta = findMeta(treeData, selectedKey);
  const activeKnowledgeBaseId = selectedMeta?.type === 'knowledge-base'
    ? selectedMeta.knowledgeBaseId
    : selectedMeta?.type === 'folder'
      ? selectedMeta.knowledgeBaseId
      : selectedMeta?.type === 'file'
        ? selectedMeta.knowledgeBaseId
        : selectedId;
  const activeTree = activeKnowledgeBaseId ? treesByKnowledgeBaseId[activeKnowledgeBaseId] : undefined;
  const activeTrashTree = activeKnowledgeBaseId ? trashTreesByKnowledgeBaseId[activeKnowledgeBaseId] : undefined;
  const expandedTreeKeys = [
    rootKey,
    categoryKey('private'),
    categoryKey('team'),
    ...knowledgeBases.map((item) => knowledgeBaseKey(item.id)),
    ...(activeTree?.folders ?? []).map((folder) => folderKey(folder.id))
  ];
  const selected = knowledgeBases.find((item) => item.id === activeKnowledgeBaseId);
  const selectedFolder = selectedMeta?.type === 'folder' ? findFolder(activeTree, selectedMeta.folderId) : undefined;
  const selectedFile = selectedMeta?.type === 'file' ? findFile(activeTree, selectedMeta.fileId) : undefined;
  const targetFolderId = selectedMeta?.type === 'folder'
    ? selectedMeta.folderId
    : selectedMeta?.type === 'file'
      ? selectedMeta.folderId ?? null
      : null;
  const targetFolder = findFolder(activeTree, targetFolderId);
  const canCreateInCurrentLocation = Boolean(activeKnowledgeBaseId);
  const canManageKnowledgeBase = selected?.current_user_role === 'admin';
  const canAuditReview = selected?.current_user_role === 'admin';
  const folderOptions = [
    { label: '根目录', value: '' },
    ...(activeTree?.folders ?? [])
      .filter((folder) => folder.id !== selectedFolder?.id)
      .map((folder) => ({ label: folder.parent_id ? `${findFolder(activeTree, folder.parent_id)?.name ?? '上级'} / ${folder.name}` : folder.name, value: folder.id }))
  ];
  const locationLabel = selected
    ? targetFolder
      ? `${selected.name} / ${targetFolder.name}`
      : selected.name
    : '请选择左侧知识库或目录';
  const canManageTrash = canManageKnowledgeBase || selected?.current_user_role === 'editor';
  const deletedFolders = (activeTrashTree?.folders ?? []).filter((folder) => folder.deleted_at);
  const deletedFiles = (activeTrashTree?.files ?? []).filter((item) => item.deleted_at);
  const deletedFolderIds = new Set(deletedFolders.map((folder) => folder.id));
  const selectedFileFolder = findFolder(activeTree, selectedFile?.folder_id);
  const selectedFolderFileCount = selectedFolder ? (activeTree?.files ?? []).filter((item) => item.folder_id === selectedFolder.id).length : 0;
  const indexedFileCount = (activeTree?.files ?? []).filter((item) => item.process_status === 'indexed').length;
  const selectedPublishGaps = publishReadinessGaps(selected);
  const reviewActions: ReviewAction[] = selected?.review_status === 'pending_review'
    ? ['publish', 'reject']
    : selected?.review_status === 'published'
      ? ['mark_needs_update', 'deprecate', 'disable_ai']
      : selected?.review_status === 'ai_disabled'
        ? ['enable_ai']
        : selected?.review_status === 'deprecated'
          ? []
          : selected?.review_status === 'needs_update'
            ? ['submit_review', 'publish', 'deprecate', 'disable_ai']
            : ['submit_review', 'deprecate', 'disable_ai'];

  const openCitationFile = (citation: { file_id: string; knowledge_base_id?: string | null }) => {
    const knowledgeBaseId = citation.knowledge_base_id ?? activeKnowledgeBaseId;
    if (!knowledgeBaseId) {
      message.warning('引用未包含可定位的知识库');
      return;
    }
    setSelectedId(knowledgeBaseId);
    setSelectedKey(fileKey(citation.file_id));
    onSelectKnowledgeBase?.(knowledgeBaseId);
  };

  const selectKnowledgeBase = (knowledgeBaseId: string | undefined, nextKey?: string) => {
    setSelectedId(knowledgeBaseId);
    if (nextKey) setSelectedKey(nextKey);
    onSelectKnowledgeBase?.(knowledgeBaseId);
  };

  useEffect(() => {
    if (!activeKnowledgeBaseId || !canManageTrash) return;
    loadTrashTree(activeKnowledgeBaseId).catch((error) => message.warning(error.message || '回收站加载失败'));
  }, [activeKnowledgeBaseId, canManageTrash]);

  useEffect(() => {
    if (!activeKnowledgeBaseId || !selected) {
      setReviewLogs([]);
      setGovernanceAudit([]);
      return;
    }
    loadReviewLogs(activeKnowledgeBaseId).catch((error) => {
      setReviewLogs([]);
      message.warning(error.message || '审核日志加载失败');
    });
    loadGovernanceAudit(activeKnowledgeBaseId).catch((error) => {
      setGovernanceAudit([]);
      message.warning(error.message || '治理变更记录加载失败');
    });
  }, [activeKnowledgeBaseId, selected?.updated_at]);

  useEffect(() => {
    folderEditForm.setFieldsValue({ name: selectedFolder?.name, parent_id: selectedFolder?.parent_id ?? '', sort_order: selectedFolder?.sort_order ?? 0 });
  }, [selectedFolder?.id]);

  useEffect(() => {
    fileEditForm.setFieldsValue({ file_name: selectedFile?.file_name, content: undefined });
    fileMoveForm.setFieldsValue({ folder_id: selectedFile?.folder_id ?? '' });
  }, [selectedFile?.id, nativePreviewRefreshVersion]);

  useEffect(() => {
    if (!selectedFile) return;
    fileGovernanceForm.setFieldsValue({
      review_status: selectedFile.review_status,
      confidentiality_level: selectedFile.confidentiality_level,
      maintainer_id: selectedFile.maintainer_id,
      expires_at: formatDateInput(selectedFile.expires_at),
      ai_usage_policy: selectedFile.ai_usage_policy,
      ai_enabled: selectedFile.ai_enabled === false ? 'false' : 'true'
    });
  }, [selectedFile?.id]);

  useEffect(() => {
    if (!selectedFile) {
      setFilePreview(undefined);
      setFilePreviewError(undefined);
      setFilePreviewLoading(false);
      setContentUrl(undefined);
      setContentType(undefined);
      setContentError(undefined);
      setContentLoading(false);
      setContentWatermark(undefined);
      setNativePreviewStatus(undefined);
      return;
    }
    let cancelled = false;
    setFilePreviewLoading(true);
    setFilePreviewError(undefined);
    agentClient.filePreview(selectedFile.id)
      .then((nextPreview) => {
        if (!cancelled) setFilePreview(nextPreview);
      })
      .catch((error) => {
        if (!cancelled) {
          setFilePreview(undefined);
          setFilePreviewError((error as Error).message || '文件预览加载失败');
        }
      })
      .finally(() => {
        if (!cancelled) setFilePreviewLoading(false);
      });

    const renderableExtensions = new Set(['.pdf', '.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx']);
    const fileExt = (selectedFile.file_ext || '').toLowerCase();
    if (renderableExtensions.has(fileExt)) {
      setContentLoading(true);
      setContentError(undefined);
      setContentUrl(undefined);
      setContentType(undefined);
      setContentWatermark(undefined);
      setNativePreviewStatus(undefined);
      let pollTimer: number | undefined;
      const loadNativeContent = () => agentClient.fileContent(selectedFile.id)
        .then(({ blob, headers }) => {
          if (cancelled) return;
          const url = URL.createObjectURL(blob);
          setContentUrl(url);
          setContentType(headers.get('content-type') || undefined);
          setContentWatermark(headers.get('x-agent-watermark') || undefined);
        })
        .catch((error) => {
          if (!cancelled) {
            setContentError((error as Error).message || '文件内容加载失败');
          }
        })
        .finally(() => {
          if (!cancelled) setContentLoading(false);
        });
      const loadNativeStatus = () => {
        agentClient.nativePreview(selectedFile.id)
          .then((status) => {
            if (cancelled) return;
            setNativePreviewStatus(status);
            if (status.status === 'native_ready') {
              loadNativeContent();
              return;
            }
            if (status.status === 'converting') {
              setContentLoading(false);
              pollTimer = window.setTimeout(loadNativeStatus, 3000);
              return;
            }
            setContentLoading(false);
            if (status.status === 'conversion_failed') {
              setContentError(status.error || 'Office 转 PDF 预览转换失败，可继续查看文本预览');
            } else if (status.status === 'blocked') {
              setContentError(status.error || '高敏文件已禁止原生内容流预览，请使用下方带水印文本预览');
            } else if (status.status === 'unavailable') {
              setContentError(status.error || '原始文件内容不可用');
            }
          })
          .catch((error) => {
            if (!cancelled) {
              setContentLoading(false);
              setContentError((error as Error).message || '原生预览状态加载失败');
            }
          });
      };
      loadNativeStatus();
      return () => {
        cancelled = true;
        if (pollTimer) window.clearTimeout(pollTimer);
      };
    } else {
      setContentUrl(undefined);
      setContentType(undefined);
      setContentError(undefined);
      setContentLoading(false);
      setContentWatermark(undefined);
      setNativePreviewStatus(undefined);
    }
    return () => {
      cancelled = true;
    };
  }, [selectedFile?.id]);

  useEffect(() => () => {
    if (contentUrl) {
      URL.revokeObjectURL(contentUrl);
    }
  }, [contentUrl]);

  useEffect(() => {
    if (!selected) return;
    knowledgeBaseSettingsForm.setFieldsValue({
      name: selected.name,
      description: selected.description,
      knowledge_type: selected.knowledge_type,
      business_domain: selected.business_domain,
      legal_domain: selected.legal_domain,
      jurisdiction: selected.jurisdiction,
      client_id: selected.client_id,
      matter_id: selected.matter_id,
      department_id: selected.department_id,
      project_team_id: selected.project_team_id,
      ethical_wall_enabled: selected.ethical_wall_enabled ? 'true' : 'false',
      review_status: selected.review_status,
      confidentiality_level: selected.confidentiality_level,
      maintainer_id: selected.maintainer_id,
      expires_at: formatDateInput(selected.expires_at),
      ai_usage_policy: selected.ai_usage_policy,
      citation_priority: selected.citation_priority,
      ai_enabled: selected.ai_enabled ? 'true' : 'false',
      default_permission_policy: selected.default_permission_policy
    });
  }, [selected?.id]);

  const normalizeKnowledgeBaseValues = <T extends { expires_at?: string | number | null; citation_priority?: string | number | null; ai_enabled?: string | boolean; ethical_wall_enabled?: string | boolean }>(values: T) => ({
    ...values,
    expires_at: normalizeExpiresAt(values.expires_at),
    citation_priority: values.citation_priority === '' || values.citation_priority == null ? 0 : Number(values.citation_priority),
    ai_enabled: values.ai_enabled === undefined ? undefined : values.ai_enabled === true || values.ai_enabled === 'true',
    ethical_wall_enabled: values.ethical_wall_enabled === undefined ? undefined : values.ethical_wall_enabled === true || values.ethical_wall_enabled === 'true'
  });

  const createKnowledgeBase = async (values: { type: 'private' | 'team'; name: string; description?: string; knowledge_type?: KnowledgeBase['knowledge_type']; review_status?: KnowledgeBase['review_status']; confidentiality_level?: KnowledgeBase['confidentiality_level']; ai_usage_policy?: KnowledgeBase['ai_usage_policy']; business_domain?: string; legal_domain?: string; jurisdiction?: string; client_id?: string; matter_id?: string; department_id?: string; project_team_id?: string; ethical_wall_enabled?: string | boolean; maintainer_id?: string; expires_at?: string | number | null; citation_priority?: string | number | null; ai_enabled?: string | boolean; default_permission_policy?: string }) => {
    setLoading(true);
    try {
      const created = await agentClient.createKnowledgeBase(normalizeKnowledgeBaseValues(values));
      message.success('知识库已创建，并已加入左侧栏目');
      knowledgeBaseForm.resetFields();
      await loadKnowledgeBases();
      await onKnowledgeBasesChanged?.();
      selectKnowledgeBase(created.id, knowledgeBaseKey(created.id));
      await loadTree(created.id);
    } finally {
      setLoading(false);
    }
  };

  const createQuickKnowledgeBase = async (values: { name: string; description?: string; knowledge_type?: KnowledgeBase['knowledge_type']; review_status?: KnowledgeBase['review_status']; confidentiality_level?: KnowledgeBase['confidentiality_level']; ai_usage_policy?: KnowledgeBase['ai_usage_policy']; maintainer_id?: string; expires_at?: string | number | null; citation_priority?: string | number | null; ai_enabled?: string | boolean }) => {
    if (!quickCreateType) return;
    await createKnowledgeBase({ ...values, type: quickCreateType });
    setQuickCreateType(undefined);
    quickCreateForm.resetFields();
  };

  const updateSelectedKnowledgeBase = async (values: Partial<{ name: string; description?: string; knowledge_type: KnowledgeBase['knowledge_type']; review_status: KnowledgeBase['review_status']; confidentiality_level: KnowledgeBase['confidentiality_level']; ai_usage_policy: KnowledgeBase['ai_usage_policy']; business_domain?: string; legal_domain?: string; jurisdiction?: string; client_id?: string; matter_id?: string; department_id?: string; project_team_id?: string; ethical_wall_enabled?: string | boolean; maintainer_id?: string; expires_at?: string | number | null; citation_priority?: string | number | null; ai_enabled?: string | boolean; default_permission_policy?: string }>) => {
    if (!activeKnowledgeBaseId) return;
    setLoading(true);
    try {
      await agentClient.updateKnowledgeBase(activeKnowledgeBaseId, normalizeKnowledgeBaseValues(values));
      message.success('知识库设置已保存');
      await loadKnowledgeBases();
      await onKnowledgeBasesChanged?.();
      await loadTree(activeKnowledgeBaseId);
    } finally {
      setLoading(false);
    }
  };

  const runReviewAction = async (action: ReviewAction, options: { comment?: string } = {}) => {
    if (!activeKnowledgeBaseId) return;
    setReviewActionLoading(action);
    try {
      const updated = await agentClient.reviewKnowledgeBase(activeKnowledgeBaseId, { action, comment: options.comment });
      message.success(`已${reviewActionLabels[action]}：${reviewStatusLabels[updated.review_status] ?? updated.review_status}`);
      await loadKnowledgeBases();
      await onKnowledgeBasesChanged?.();
      await Promise.all([loadTree(activeKnowledgeBaseId), loadReviewLogs(activeKnowledgeBaseId), loadGovernanceAudit(activeKnowledgeBaseId)]);
    } catch (error) {
      message.error((error as Error).message || `${reviewActionLabels[action]}失败`);
    } finally {
      setReviewActionLoading(undefined);
    }
  };

  const handleFeedback = async (feedbackId: string, status: AiAssistantFeedback['status']) => {
    setQualityLoading(true);
    try {
      await agentClient.handleAiAssistantFeedback(feedbackId, { status });
      message.success(`反馈已标记为${feedbackStatusLabels[status]}`);
      await loadQualityFeedback();
    } finally {
      setQualityLoading(false);
    }
  };

  const confirmReviewAction = (action: ReviewAction) => {
    if (!selected) return;
    const publishGaps = publishReadinessGaps(selected);
    if (action === 'publish' && publishGaps.length) {
      message.warning(`发布前请先补齐：${publishGaps.join('、')}`);
      return;
    }
    let comment = '';
    Modal.confirm({
      title: `${reviewActionLabels[action]}知识库`,
      content: action === 'reject' ? (
        <Input.TextArea
          autoFocus
          placeholder="请输入退回原因，审核日志会保留该说明"
          autoSize={{ minRows: 3, maxRows: 5 }}
          onChange={(event) => {
            comment = event.target.value;
          }}
        />
      ) : (
        <Typography.Paragraph style={{ marginBottom: 0 }}>
          当前状态为“{reviewStatusLabels[selected.review_status] ?? selected.review_status}”。确认执行“{reviewActionLabels[action]}”后，后端会按审核资质、提交人与审核人分离、高影响知识发布门槛进行校验。
        </Typography.Paragraph>
      ),
      okText: reviewActionLabels[action],
      cancelText: '取消',
      okButtonProps: { danger: action === 'reject' || action === 'deprecate' || action === 'disable_ai' },
      onOk: () => {
        if (action === 'reject' && !comment.trim()) {
          message.warning('退回必须填写原因');
          return Promise.reject(new Error('reject reason is required'));
        }
        return runReviewAction(action, { comment: comment.trim() });
      }
    });
  };

  const deleteSelectedKnowledgeBase = async () => {
    if (!activeKnowledgeBaseId) return;
    setLoading(true);
    try {
      await agentClient.deleteKnowledgeBase(activeKnowledgeBaseId);
      message.success('知识库已删除');
      const next = await agentClient.knowledgeBases();
      setKnowledgeBases(next);
      await onKnowledgeBasesChanged?.();
      const nextSelected = next[0];
      selectKnowledgeBase(nextSelected?.id, nextSelected ? knowledgeBaseKey(nextSelected.id) : categoryKey('private'));
    } finally {
      setLoading(false);
    }
  };

  const createFolder = async (values: { name: string }) => {
    if (!activeKnowledgeBaseId) return;
    setLoading(true);
    try {
      const created = await agentClient.createFolder({ knowledge_base_id: activeKnowledgeBaseId, parent_id: targetFolderId, name: values.name });
      message.success('文件夹已创建');
      folderForm.resetFields();
      setSelectedId(activeKnowledgeBaseId);
      setSelectedKey(folderKey(created.id));
      await loadTree(activeKnowledgeBaseId);
      await loadGovernanceAudit(activeKnowledgeBaseId);
    } finally {
      setLoading(false);
    }
  };

  const uploadFile = async () => {
    if (!activeKnowledgeBaseId || !file) return;
    setLoading(true);
    try {
      const contentBase64 = await fileToBase64(file);
      const uploaded = await agentClient.uploadKnowledgeFile(activeKnowledgeBaseId, file.name, contentBase64, targetFolderId ?? undefined);
      message.success(uploaded.deduplicated ? '文件内容已存在，已复用原文件并确认任务' : '文件已上传并进入处理队列');
      setFile(null);
      setFileInputVersion((current) => current + 1);
      setSelectedId(activeKnowledgeBaseId);
      setSelectedKey(fileKey(uploaded.id));
      await loadTree(activeKnowledgeBaseId);
    } finally {
      setLoading(false);
    }
  };

  const createTextFile = async (values: { file_name: string; content: string }) => {
    if (!activeKnowledgeBaseId) return;
    setLoading(true);
    try {
      const uploaded = await agentClient.uploadKnowledgeFile(activeKnowledgeBaseId, values.file_name, textToBase64(values.content), targetFolderId ?? undefined);
      message.success('文件已创建并进入处理队列');
      textFileForm.resetFields();
      setSelectedId(activeKnowledgeBaseId);
      setSelectedKey(fileKey(uploaded.id));
      await loadTree(activeKnowledgeBaseId);
    } finally {
      setLoading(false);
    }
  };

  const updateSelectedFolder = async (values: { name: string; parent_id?: string; sort_order?: number }) => {
    if (!selectedFolder || !activeKnowledgeBaseId) return;
    setLoading(true);
    try {
      await agentClient.updateFolder(selectedFolder.id, { name: values.name, parent_id: values.parent_id || null, sort_order: Number(values.sort_order ?? 0) });
      message.success('文件夹已更新');
      await loadTree(activeKnowledgeBaseId);
    } finally {
      setLoading(false);
    }
  };

  const deleteSelectedFolder = async () => {
    if (!selectedFolder || !activeKnowledgeBaseId) return;
    setLoading(true);
    try {
      await agentClient.deleteFolder(selectedFolder.id);
      message.success('文件夹已删除');
      setSelectedKey(knowledgeBaseKey(activeKnowledgeBaseId));
      await Promise.all([loadTree(activeKnowledgeBaseId), loadTrashTree(activeKnowledgeBaseId)]);
    } finally {
      setLoading(false);
    }
  };

  const moveSelectedFile = async (values: { folder_id?: string }) => {
    if (!selectedFile || !activeKnowledgeBaseId) return;
    setLoading(true);
    try {
      await agentClient.updateFile(selectedFile.id, { folder_id: values.folder_id || null });
      message.success('文件位置已更新');
      await loadTree(activeKnowledgeBaseId);
    } finally {
      setLoading(false);
    }
  };

  const updateSelectedFileBasic = async (values: { file_name: string; content?: string }) => {
    if (!selectedFile || !activeKnowledgeBaseId) return;
    const payload: { file_name?: string; content_base64?: string } = {};
    if (values.file_name && values.file_name !== selectedFile.file_name) payload.file_name = values.file_name;
    if (values.content !== undefined && values.content !== '') payload.content_base64 = textToBase64(values.content);
    if (!payload.file_name && !payload.content_base64) {
      message.info('没有需要保存的文件变更');
      return;
    }
    setLoading(true);
    try {
      const updated = await agentClient.updateFile(selectedFile.id, payload);
      message.success(payload.content_base64 ? '文件名称/内容已保存，并已重新进入索引队列' : '文件名称已保存');
      setSelectedKey(fileKey(updated.id));
      fileEditForm.setFieldsValue({ file_name: updated.file_name, content: undefined });
      await loadTree(activeKnowledgeBaseId);
    } finally {
      setLoading(false);
    }
  };

  const updateSelectedFileGovernance = async (values: { review_status?: KnowledgeBase['review_status']; confidentiality_level?: KnowledgeBase['confidentiality_level']; maintainer_id?: string; expires_at?: string | number | null; ai_usage_policy?: KnowledgeBase['ai_usage_policy']; ai_enabled?: string | boolean }) => {
    if (!selectedFile || !activeKnowledgeBaseId) return;
    setLoading(true);
    try {
      await agentClient.updateFile(selectedFile.id, normalizeKnowledgeBaseValues(values));
      message.success('文件设置已保存');
      await loadTree(activeKnowledgeBaseId);
    } finally {
      setLoading(false);
    }
  };

  const deleteSelectedFile = async () => {
    if (!selectedFile || !activeKnowledgeBaseId) return;
    setLoading(true);
    try {
      await agentClient.deleteFile(selectedFile.id);
      message.success('文件已删除');
      setSelectedKey(selectedFile.folder_id ? folderKey(selectedFile.folder_id) : knowledgeBaseKey(activeKnowledgeBaseId));
      await Promise.all([loadTree(activeKnowledgeBaseId), loadTrashTree(activeKnowledgeBaseId)]);
    } finally {
      setLoading(false);
    }
  };

  const restoreDeletedFolder = async (folderId: string) => {
    if (!activeKnowledgeBaseId) return;
    setTrashLoading(true);
    try {
      await agentClient.restoreFolder(folderId);
      message.success('文件夹已恢复');
      await Promise.all([loadTree(activeKnowledgeBaseId), loadTrashTree(activeKnowledgeBaseId)]);
    } finally {
      setTrashLoading(false);
    }
  };

  const restoreDeletedFile = async (fileId: string) => {
    if (!activeKnowledgeBaseId) return;
    setTrashLoading(true);
    try {
      await agentClient.restoreFile(fileId);
      message.success('文件已恢复');
      await Promise.all([loadTree(activeKnowledgeBaseId), loadTrashTree(activeKnowledgeBaseId)]);
    } finally {
      setTrashLoading(false);
    }
  };

  return (
    <div className="knowledge-workbench">
      <Card
        title="知识库"
        className="knowledge-sidebar-card"
        extra={<Button type="link" loading={loading} onClick={() => loadKnowledgeBases().catch((error) => message.error(error.message))}>刷新</Button>}
      >
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 4 }}>
            按你的固定目录展开：个人知识库与共享知识库常驻左侧，点击知识库或文件后在中间打开。
          </Typography.Paragraph>
          <Input.Search allowClear placeholder="按名称或描述筛选" value={keyword} onChange={(event) => setKeyword(event.target.value)} />
          <Select
            value={typeFilter}
            onChange={setTypeFilter}
            options={[{ label: '全部归属', value: 'all' }, { label: '个人知识库', value: 'private' }, { label: '共享知识库', value: 'team' }]}
          />
          <Select
            value={knowledgeTypeFilter}
            onChange={setKnowledgeTypeFilter}
            options={[{ label: '全部知识类型', value: 'all' }, ...knowledgeTypeOptions]}
          />
          <Select
            value={reviewStatusFilter}
            onChange={setReviewStatusFilter}
            options={[{ label: '全部审核状态', value: 'all' }, ...reviewStatusOptions]}
          />
          <Select
            value={aiPolicyFilter}
            onChange={setAiPolicyFilter}
            options={[{ label: '全部 AI 策略', value: 'all' }, ...aiUsagePolicyOptions]}
          />
            <Tree
              className="knowledge-tree"
              blockNode
              expandedKeys={expandedTreeKeys}
              selectedKeys={[selectedKey]}
              treeData={treeData}
              showLine
              onSelect={(keys) => {
                const nextKey = String(keys[0] ?? selectedKey);
                const nextMeta = findMeta(treeData, nextKey);
                if (!nextMeta) return;
                setSelectedKey(nextKey);
                if (nextMeta.type === 'knowledge-base') {
                  selectKnowledgeBase(nextMeta.knowledgeBaseId);
                }
                if (nextMeta.type === 'folder' || nextMeta.type === 'file') {
                  selectKnowledgeBase(nextMeta.knowledgeBaseId);
                }
              }}
            />
        </Space>
      </Card>

      <Space direction="vertical" size="middle" className="knowledge-content-panel">
          {!selected && (
          <Card title="新建知识库">
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                <Form
                form={knowledgeBaseForm}
                layout="inline"
                className="responsive-inline-form"
                onFinish={createKnowledgeBase}
                 initialValues={{ type: selectedMeta?.type === 'category' && selectedMeta.knowledgeBaseType !== 'case' ? selectedMeta.knowledgeBaseType : 'private', review_status: 'published', confidentiality_level: 'internal', ai_usage_policy: 'allow_generation', ai_enabled: 'true', citation_priority: 0, default_permission_policy: 'private' }}
              >
                <Form.Item name="type" rules={[{ required: true }]}> 
                  <Select
                    style={{ width: 140 }}
                    options={[
                      { label: '个人知识库', value: 'private' },
                      { label: '共享知识库', value: 'team' }
                    ]}
                  />
                </Form.Item>
                <Form.Item name="name" rules={[{ required: true, message: '请输入知识库名称' }]}> 
                  <Input placeholder="知识库名称" style={{ width: 240 }} />
                </Form.Item>
                <Form.Item name="description"> 
                  <Input placeholder="描述，可选" style={{ width: 280 }} />
                </Form.Item>
                <Form.Item name="knowledge_type" initialValue="general">
                  <Select style={{ width: 160 }} options={knowledgeTypeOptions} />
                </Form.Item>
                <Form.Item name="review_status" initialValue="published">
                  <Select style={{ width: 140 }} options={reviewStatusOptions} />
                </Form.Item>
                <Form.Item name="confidentiality_level" initialValue="internal">
                  <Select style={{ width: 120 }} options={confidentialityOptions} />
                </Form.Item>
                <Form.Item name="ai_usage_policy" initialValue="allow_generation">
                  <Select style={{ width: 170 }} options={aiUsagePolicyOptions} />
                </Form.Item>
                <Form.Item name="ai_enabled">
                  <Select style={{ width: 100 }} options={[{ label: '启用 AI', value: 'true' }, { label: '禁用 AI', value: 'false' }]} />
                </Form.Item>
                <Form.Item name="maintainer_id">
                  <Select allowClear showSearch optionFilterProp="label" placeholder="维护人" style={{ width: 170 }} options={userOptions} />
                </Form.Item>
                <Form.Item name="expires_at">
                  <Input type="date" style={{ width: 160 }} />
                </Form.Item>
                <Form.Item name="citation_priority">
                  <Input type="number" placeholder="引用优先级" style={{ width: 120 }} />
                </Form.Item>
                <Form.Item name="default_permission_policy">
                  <Select style={{ width: 120 }} options={[{ label: '私有', value: 'private' }, { label: '案件成员', value: 'case_members' }]} />
                </Form.Item>
                <Button type="primary" htmlType="submit" loading={loading}>新建知识库</Button>
              </Form>
              <Button loading={loading} onClick={createRequiredKnowledgeBases}>补齐指定知识库结构</Button>
            </Space>
          </Card>
          )}

          <Card title={`当前位置：${locationLabel}`}>
            {selected ? (
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                <Space wrap>
                  <Tag>{typeLabels[selected.type]}</Tag>
                  <Tag color="blue">{knowledgeTypeLabels[selected.knowledge_type] ?? selected.knowledge_type}</Tag>
                  <Tag color={selected.review_status === 'published' ? 'green' : selected.review_status === 'ai_disabled' ? 'red' : 'orange'}>{reviewStatusLabels[selected.review_status] ?? selected.review_status}</Tag>
                  <Tag color={selected.confidentiality_level === 'restricted' ? 'red' : selected.confidentiality_level === 'confidential' ? 'orange' : undefined}>{confidentialityLabels[selected.confidentiality_level] ?? selected.confidentiality_level}</Tag>
                  <Tag>{aiUsagePolicyLabels[selected.ai_usage_policy] ?? selected.ai_usage_policy}</Tag>
                  <Tag>{selected.status}</Tag>
                  <Tag>{selected.default_permission_policy}</Tag>
                  {selectedFolder && <Tag color="blue">当前文件夹：{selectedFolder.name}</Tag>}
                  {selectedFile && <Tag color="green">当前文件：{selectedFile.file_name}</Tag>}
                  {selectedFile?.is_high_sensitive && <Tag color="red">高敏文件：AI 已禁用</Tag>}
                </Space>

                <Card
                  size="small"
                  title="质量反馈闭环（P0）"
                  extra={<Button size="small" loading={qualityLoading} onClick={() => loadQualityFeedback().catch((error) => message.warning(error.message || '质量反馈刷新失败'))}>刷新</Button>}
                >
                  <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                    <Alert
                      type="info"
                      showIcon
                      message="反馈明细仅在律师侧 Agent 本地可见"
                      description="平台侧如需健康上报，只能接收聚合计数，不得包含问题正文、回答正文、文件名或备注内容。"
                    />
                    <div className="quality-feedback-grid">
                      <div><Typography.Text type="secondary">反馈总数</Typography.Text><Typography.Title level={4}>{enterpriseOverview?.ai_feedback_total_count ?? 0}</Typography.Title></div>
                      <div><Typography.Text type="secondary">差评数量</Typography.Text><Typography.Title level={4}>{enterpriseOverview?.ai_feedback_negative_count ?? 0}</Typography.Title></div>
                      <div><Typography.Text type="secondary">引用缺失</Typography.Text><Typography.Title level={4}>{enterpriseOverview?.ai_feedback_citation_missing_count ?? 0}</Typography.Title></div>
                      <div><Typography.Text type="secondary">证据不足</Typography.Text><Typography.Title level={4}>{enterpriseOverview?.ai_feedback_insufficient_evidence_count ?? 0}</Typography.Title></div>
                      <div><Typography.Text type="secondary">答案不准确</Typography.Text><Typography.Title level={4}>{enterpriseOverview?.ai_feedback_answer_inaccurate_count ?? enterpriseOverview?.ai_feedback_issue_counts?.answer_inaccurate ?? 0}</Typography.Title></div>
                      <div><Typography.Text type="secondary">权限异常</Typography.Text><Typography.Title level={4}>{enterpriseOverview?.ai_feedback_permission_anomaly_count ?? enterpriseOverview?.ai_feedback_issue_counts?.permission_anomaly ?? 0}</Typography.Title></div>
                    </div>
                    <Table<AiAssistantFeedback>
                      rowKey="id"
                      size="small"
                      loading={qualityLoading}
                      dataSource={aiFeedbacks.slice(0, 8)}
                      pagination={false}
                      scroll={{ x: 860 }}
                      locale={{ emptyText: <Empty description="暂无 AI 质量反馈" /> }}
                      columns={[
                        { title: '评分', dataIndex: 'rating', render: (rating: AiAssistantFeedback['rating']) => <Tag color={rating === 'down' ? 'red' : rating === 'up' ? 'green' : undefined}>{rating === 'down' ? '需改进' : rating === 'up' ? '有帮助' : '中立'}</Tag> },
                        { title: '问题类型', dataIndex: 'issue_label', render: (label?: string | null) => feedbackIssueLabels[String(label ?? '')] ?? label ?? '-' },
                        { title: '状态', dataIndex: 'status', render: (status: AiAssistantFeedback['status']) => <Tag color={status === 'open' ? 'orange' : status === 'resolved' ? 'green' : undefined}>{feedbackStatusLabels[status]}</Tag> },
                        { title: '备注', dataIndex: 'comment', ellipsis: true, render: (value?: string | null) => value || '-' },
                        { title: '时间', dataIndex: 'created_at', render: formatTime },
                        {
                          title: '处理',
                          fixed: 'right',
                          render: (_, record) => (
                            <Space>
                              <Button size="small" disabled={record.status === 'resolved'} loading={qualityLoading} onClick={() => handleFeedback(record.id, 'resolved')}>解决</Button>
                              <Button size="small" disabled={record.status === 'ignored'} loading={qualityLoading} onClick={() => handleFeedback(record.id, 'ignored')}>忽略</Button>
                            </Space>
                          )
                        }
                      ]}
                    />
                  </Space>
                </Card>

                <Card size="small" title="审核发布与治理" className="knowledge-review-card">
                  <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                    {highImpactKnowledgeTypes.has(selected.knowledge_type) && selectedPublishGaps.length > 0 && (
                      <Alert
                        type="warning"
                        showIcon
                        message="高影响知识发布前仍有缺失项"
                        description={`模板、条款和文书类知识需要先补齐 ${selectedPublishGaps.join('、')}，否则后端会拒绝发布。`}
                      />
                    )}
                    {selected.review_status === 'pending_review' && (
                      <Alert
                        type="info"
                        showIcon
                        message="待审核状态"
                        description="发布或退回会触发后端审核资质校验；非平台管理员不能自提自审。"
                      />
                    )}
                    {!canAuditReview && (
                      <Alert type="warning" showIcon message="当前账号无审核操作入口" description="需要知识库管理员身份；实际发布还会由后端校验本地角色、组织维度审核人和提交人与审核人分离规则。" />
                    )}
                    <Space wrap>
                      {reviewActions.map((action) => {
                        const disabled = !canAuditReview || (action === 'publish' && selectedPublishGaps.length > 0);
                        return (
                          <Button
                            key={action}
                            danger={action === 'reject' || action === 'deprecate' || action === 'disable_ai'}
                            type={action === 'publish' ? 'primary' : 'default'}
                            loading={reviewActionLoading === action}
                            disabled={disabled}
                            onClick={() => confirmReviewAction(action)}
                          >
                            {reviewActionLabels[action]}
                          </Button>
                        );
                      })}
                      <Button loading={reviewLogsLoading} disabled={!activeKnowledgeBaseId} onClick={() => activeKnowledgeBaseId && loadReviewLogs(activeKnowledgeBaseId).catch((error) => message.warning(error.message || '审核日志刷新失败'))}>刷新审核日志</Button>
                    </Space>
                    <Form form={knowledgeBaseSettingsForm} layout="vertical" onFinish={updateSelectedKnowledgeBase} disabled={!canManageKnowledgeBase}>
                      <div className="knowledge-governance-grid">
                        <Form.Item name="name" label="知识库名称" rules={[{ required: true, message: '请输入知识库名称' }]}> 
                          <Input />
                        </Form.Item>
                        <Form.Item name="knowledge_type" label="知识类型">
                          <Select options={knowledgeTypeOptions} />
                        </Form.Item>
                        <Form.Item name="confidentiality_level" label="保密等级">
                          <Select options={confidentialityOptions} />
                        </Form.Item>
                        <Form.Item name="ai_usage_policy" label="AI 使用规则">
                          <Select options={aiUsagePolicyOptions} />
                        </Form.Item>
                        <Form.Item name="ai_enabled" label="AI 开关">
                          <Select options={[{ label: '启用', value: 'true' }, { label: '禁用', value: 'false' }]} />
                        </Form.Item>
                        <Form.Item name="maintainer_id" label="维护人">
                          <Select allowClear showSearch optionFilterProp="label" options={userOptions} />
                        </Form.Item>
                        <Form.Item name="expires_at" label="有效期">
                          <Input type="date" placeholder="为空表示长期有效" />
                        </Form.Item>
                        <Form.Item name="citation_priority" label="引用优先级">
                          <Input type="number" placeholder="高影响知识发布前需大于 0" />
                        </Form.Item>
                        <Form.Item name="default_permission_policy" label="默认权限策略">
                          <Select options={[{ label: '私有', value: 'private' }, { label: '案件成员', value: 'case_members' }]} />
                        </Form.Item>
                      </div>
                      <Form.Item name="description" label="描述">
                        <Input.TextArea autoSize={{ minRows: 2, maxRows: 5 }} />
                      </Form.Item>
                      <div className="knowledge-review-actions-row">
                        <Button htmlType="submit" loading={loading} disabled={!canManageKnowledgeBase}>保存治理设置</Button>
                        <Popconfirm title="确认删除该知识库？" description="知识库、目录和文件会被软删除并写入本地审计日志。" onConfirm={deleteSelectedKnowledgeBase} okText="确认删除" cancelText="取消">
                          <Button danger loading={loading} disabled={!canManageKnowledgeBase}>删除知识库</Button>
                        </Popconfirm>
                      </div>
                    </Form>
                    <Table<KnowledgeBaseReviewLog>
                      rowKey="id"
                      size="small"
                      title={() => `审核日志（${reviewLogs.length}）`}
                      loading={reviewLogsLoading}
                      dataSource={reviewLogs}
                      pagination={{ pageSize: 5 }}
                      scroll={{ x: 760 }}
                      locale={{ emptyText: <Empty description="暂无审核日志" /> }}
                      columns={[
                        { title: '动作', dataIndex: 'action', render: (action: string) => reviewActionLabels[action as ReviewAction] ?? action },
                        { title: '状态流转', render: (_, record) => `${reviewStatusLabels[record.from_status] ?? record.from_status} → ${reviewStatusLabels[record.to_status] ?? record.to_status}` },
                        { title: '操作人', dataIndex: 'operator_id', render: (operatorId: string) => users.find((user) => user.id === operatorId)?.name ?? operatorId },
                        { title: '说明', dataIndex: 'comment', ellipsis: true, render: (value?: string | null) => value || '-' },
                        { title: '时间', dataIndex: 'created_at', render: formatTime }
                      ]}
                    />
                    <Table<KnowledgeBaseGovernanceAudit>
                      rowKey="id"
                      size="small"
                      title={() => `治理变更记录（${governanceAudit.length}）`}
                      loading={governanceAuditLoading}
                      dataSource={governanceAudit}
                      pagination={{ pageSize: 6 }}
                      scroll={{ x: 900 }}
                      locale={{ emptyText: <Empty description="暂无治理字段变更记录" /> }}
                      columns={[
                        { title: '字段', dataIndex: 'field_name', render: (fieldName: string) => governanceFieldLabels[fieldName] ?? fieldName },
                        { title: '变更前', dataIndex: 'old_value', ellipsis: true, render: (value: string | null | undefined, record: KnowledgeBaseGovernanceAudit) => renderGovernanceAuditValue(record.field_name, value) },
                        { title: '变更后', dataIndex: 'new_value', ellipsis: true, render: (value: string | null | undefined, record: KnowledgeBaseGovernanceAudit) => renderGovernanceAuditValue(record.field_name, value) },
                        { title: '操作人', dataIndex: 'operator_id', render: (operatorId: string) => users.find((user) => user.id === operatorId)?.name ?? operatorId },
                        { title: '时间', dataIndex: 'created_at', render: formatTime }
                      ]}
                    />
                  </Space>
                </Card>

                <Card size="small" title="基础文件预览" className="knowledge-preview-card">
                  {selectedFile ? (
                    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                      <div className="knowledge-preview-heading">
                        <div>
                          <Typography.Text strong>{selectedFile.file_name}</Typography.Text>
                          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
                            {selectedFileFolder ? `${selected.name} / ${selectedFileFolder.name}` : `${selected.name} / 根目录`}
                          </Typography.Paragraph>
                        </div>
                        <Space wrap>
                          <Tag color={selectedFile.process_status === 'indexed' ? 'green' : selectedFile.process_status === 'failed' ? 'red' : selectedFile.process_status === 'ai_disabled' ? 'red' : 'orange'}>{selectedFile.process_status}</Tag>
                          {selectedFile.is_high_sensitive && <Tag color="red">高敏</Tag>}
                          <Tag>{selectedFile.file_ext || '未知类型'}</Tag>
                          <Tag>{formatFileSize(selectedFile.file_size)}</Tag>
                        </Space>
                      </div>
                      <div className="knowledge-preview-meta-grid">
                        <div><Typography.Text type="secondary">文件路径</Typography.Text><Typography.Text copyable>{selectedFile.file_path || '-'}</Typography.Text></div>
                        <div><Typography.Text type="secondary">审核状态</Typography.Text><Typography.Text>{reviewStatusLabels[String(selectedFile.review_status)] ?? selectedFile.review_status ?? '-'}</Typography.Text></div>
                        <div><Typography.Text type="secondary">保密等级</Typography.Text><Typography.Text>{confidentialityLabels[String(selectedFile.confidentiality_level)] ?? selectedFile.confidentiality_level ?? '-'}</Typography.Text></div>
                        <div><Typography.Text type="secondary">AI 规则</Typography.Text><Typography.Text>{aiUsagePolicyLabels[String(selectedFile.ai_usage_policy)] ?? selectedFile.ai_usage_policy ?? '-'}</Typography.Text></div>
                        <div><Typography.Text type="secondary">高敏识别</Typography.Text><Typography.Text>{selectedFile.is_high_sensitive ? `已命中：${selectedFile.sensitive_signal_types?.join('、') || '高敏信号'}` : '未命中'}</Typography.Text></div>
                      </div>
                      {selectedFile.is_high_sensitive && (
                        <Alert type="warning" showIcon message="该文件已被自动标记为高敏" description="解析阶段命中身份证号、手机号、银行卡号等高敏信号，后端已默认禁止该文件进入 AI 检索和生成，并禁用 PDF/图片/Office 原生内容流预览。" />
                      )}
                      {nativePreviewStatus?.status === 'converting' && (
                        <Alert
                          type="info"
                          showIcon
                          message="Office 版式预览正在转换"
                          description={`后台任务 ${nativePreviewStatus.task_id ?? '-'} 正在生成 PDF，当前可先查看下方文本预览。`}
                          action={<Button size="small" loading={nativePreviewActionLoading} onClick={runSelectedNativePreview}>立即转换</Button>}
                        />
                      )}
                      {nativePreviewStatus?.status === 'native_ready' && nativePreviewStatus.content_type === 'application/pdf' && !contentUrl && !contentLoading && <Alert type="success" showIcon message="Office 版式预览已就绪" description="正在读取转换后的 PDF 预览缓存。" />}
                      {contentLoading && <Alert type="info" showIcon message="正在加载原生文件预览" description="PDF、图片和已转换的 Office PDF 会以内嵌方式打开，其余格式继续展示文本预览。" />}
                      {contentError && <Alert type="warning" showIcon message={nativePreviewStatus?.status === 'blocked' ? '原生预览已降级' : '原生预览加载失败'} description={contentError} action={nativePreviewStatus?.status === 'conversion_failed' ? <Button size="small" loading={nativePreviewActionLoading} onClick={runSelectedNativePreview}>重试转换</Button> : undefined} />}
                      {contentUrl && contentType?.includes('application/pdf') && (
                        <div className="knowledge-preview-native-panel">
                          <Space wrap size={[8, 8]} style={{ marginBottom: 10 }}>
                            <Tag color="red">{selectedFile.file_ext?.toLowerCase() === '.pdf' ? 'PDF 原生预览' : 'Office 转 PDF 预览'}</Tag>
                            {contentType && <Tag>{contentType}</Tag>}
                          </Space>
                          {contentWatermark && <Alert type="info" showIcon className="knowledge-preview-watermark-banner" message="预览水印已写入本地审计" description={`水印：${contentWatermark}`} />}
                          <div className="knowledge-preview-native-stage">
                            <iframe className="knowledge-preview-frame" src={contentUrl} title={selectedFile.file_name} />
                            {contentWatermark && <div className="knowledge-preview-watermark-overlay">{contentWatermark}</div>}
                          </div>
                        </div>
                      )}
                      {contentUrl && ['.png', '.jpg', '.jpeg', '.bmp', '.tiff'].includes(selectedFile.file_ext?.toLowerCase() || '') && (
                        <div className="knowledge-preview-native-panel">
                          <Space wrap size={[8, 8]} style={{ marginBottom: 10 }}>
                            <Tag color="blue">图片原生预览</Tag>
                            {contentType && <Tag>{contentType}</Tag>}
                          </Space>
                          {contentWatermark && <Alert type="info" showIcon className="knowledge-preview-watermark-banner" message="预览水印已写入本地审计" description={`水印：${contentWatermark}`} />}
                          <div className="knowledge-preview-native-stage">
                            <img className="knowledge-preview-image" src={contentUrl} alt={selectedFile.file_name} />
                            {contentWatermark && <div className="knowledge-preview-watermark-overlay">{contentWatermark}</div>}
                          </div>
                        </div>
                      )}
                      {filePreviewLoading && <Alert type="info" showIcon message="正在加载文件正文预览" description="优先读取已索引 chunk；未索引文件会尝试从本地文件读取短预览。" />}
                      {filePreviewError && <Alert type="warning" showIcon message="文件预览加载失败" description={filePreviewError} />}
                      {filePreview && filePreview.file.id === selectedFile.id && (
                        <div className="knowledge-preview-text-panel">
                          <Space wrap size={[8, 8]} style={{ marginBottom: 10 }}>
                            <Tag color={filePreview.source === 'chunks' ? 'green' : filePreview.source === 'raw_file' ? 'blue' : 'orange'}>
                              {filePreview.source === 'chunks' ? '索引片段预览' : filePreview.source === 'raw_file' ? '原文件预览' : '正文不可用'}
                            </Tag>
                            <Tag>chunk {filePreview.chunk_count}</Tag>
                            {filePreview.truncated && <Tag color="orange">已截断</Tag>}
                          </Space>
                          <Alert
                            type="info"
                            showIcon
                            className="knowledge-preview-watermark-banner"
                            message="预览水印已写入本地审计"
                            description={`水印：${filePreview.watermark.watermark_text}`}
                          />
                          {filePreview.high_risk_event && (
                            <Alert
                              type="warning"
                              showIcon
                              className="knowledge-preview-watermark-banner"
                              message="本次预览已记录为高风险访问"
                              description={`原因：${filePreview.high_risk_event.risk_reasons.join('、')}`}
                            />
                          )}
                          {filePreview.error ? (
                            <Alert type="warning" showIcon message="正文不可用" description={filePreview.error} />
                          ) : (
                            <pre className="knowledge-preview-text-block" data-watermark={filePreview.watermark.watermark_text}>{filePreview.text || '暂无可展示正文'}</pre>
                          )}
                          {filePreview.chunks.length > 0 && (
                            <Card size="small" title="索引片段与引用定位" className="knowledge-preview-chunks-card">
                              <Table
                                rowKey="chunk_id"
                                size="small"
                                dataSource={filePreview.chunks.slice(0, 12)}
                                pagination={false}
                                scroll={{ x: 760 }}
                                columns={[
                                  { title: '序号', dataIndex: 'chunk_index', width: 80 },
                                  { title: '页码', dataIndex: 'page_number', width: 80, render: (value) => value ?? '-' },
                                  { title: '段落', dataIndex: 'paragraph_ref', width: 100, render: (value) => value || '-' },
                                  { title: '片段内容', dataIndex: 'text', ellipsis: true }
                                ]}
                              />
                              {filePreview.chunks.length > 12 && <Typography.Text type="secondary">仅展示前 12 个片段，完整检索由右侧 AI 引用来源定位。</Typography.Text>}
                            </Card>
                          )}
                        </div>
                      )}
                      <div className="knowledge-preview-body">
                        <Typography.Text strong>预览说明</Typography.Text>
                        <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
                          当前正文预览由 /api/agent/files/{'{file_id}'}/preview 返回；PDF、图片和 Office 版式预览先通过 /native-preview 查询状态，再从 /content 读取受本地访问控制和水印保护的内容流。选中文件后，右侧提问会以 current_file 范围调用 /api/agent/ai/query。
                        </Typography.Paragraph>
                      </div>
                    </Space>
                  ) : selectedFolder ? (
                    <Alert
                      type="info"
                      showIcon
                      message={`当前文件夹：${selectedFolder.name}`}
                      description={`该文件夹下直接包含 ${selectedFolderFileCount} 个文件。请选择左侧具体文件后查看文件预览，并让右侧 AI 对话锁定 current_file 范围。`}
                    />
                  ) : (
                    <Alert
                      type="info"
                      showIcon
                      message={`当前知识库：${selected.name}`}
                      description={`已加载 ${(activeTree?.folders ?? []).length} 个文件夹、${(activeTree?.files ?? []).length} 个文件，其中 ${indexedFileCount} 个文件已完成索引。请选择左侧文件进入文件级预览。`}
                    />
                  )}
                </Card>

                {selectedFolder && (
                  <Card size="small" title="当前文件夹管理">
                    <Form form={folderEditForm} layout="inline" className="responsive-inline-form" onFinish={updateSelectedFolder}>
                      <Form.Item name="name" rules={[{ required: true, message: '请输入文件夹名称' }]}> 
                        <Input placeholder="文件夹名称" style={{ width: 220 }} />
                      </Form.Item>
                      <Form.Item name="parent_id">
                        <Select style={{ width: 220 }} options={folderOptions} />
                      </Form.Item>
                      <Form.Item name="sort_order">
                        <Input type="number" placeholder="排序" style={{ width: 100 }} />
                      </Form.Item>
                      <Button htmlType="submit" loading={loading}>保存文件夹</Button>
                      <Popconfirm title="确认删除该文件夹？" description="删除会同时隐藏该文件夹下的子文件夹和文件，可由后端恢复接口恢复。" onConfirm={deleteSelectedFolder} okText="确认删除" cancelText="取消">
                        <Button danger loading={loading}>删除文件夹</Button>
                      </Popconfirm>
                    </Form>
                  </Card>
                )}

                {selectedFile && (
                  <Card size="small" title="当前文件管理">
                    <Space direction="vertical" style={{ width: '100%' }} size="middle">
                      <Form form={fileEditForm} layout="vertical" onFinish={updateSelectedFileBasic}>
                        <div className="knowledge-text-file-grid">
                          <Form.Item name="file_name" label="文件名" rules={[{ required: true, message: '请输入文件名' }]}> 
                            <Input placeholder="例如：学习笔记.md" />
                          </Form.Item>
                          <Form.Item name="content" label="替换文本内容">
                            <Input.TextArea placeholder="可选：输入后会覆盖当前文件内容，并重新进入解析索引队列" autoSize={{ minRows: 3, maxRows: 10 }} />
                          </Form.Item>
                        </div>
                        <Button type="primary" htmlType="submit" loading={loading}>保存文件名/内容</Button>
                      </Form>
                      <Form form={fileMoveForm} layout="inline" className="responsive-inline-form" onFinish={moveSelectedFile}>
                        <Form.Item name="folder_id">
                          <Select style={{ width: 240 }} options={folderOptions} />
                        </Form.Item>
                        <Button htmlType="submit" loading={loading}>移动文件</Button>
                        <Popconfirm title="确认删除该文件？" description="文件会被软删除并写入本地审计日志。" onConfirm={deleteSelectedFile} okText="确认删除" cancelText="取消">
                          <Button danger loading={loading}>删除文件</Button>
                        </Popconfirm>
                      </Form>
                      <Form form={fileGovernanceForm} layout="vertical" onFinish={updateSelectedFileGovernance}>
                        <div className="knowledge-governance-grid">
                          <Form.Item name="review_status" label="文件审核状态">
                            <Select options={reviewStatusOptions} />
                          </Form.Item>
                          <Form.Item name="confidentiality_level" label="文件保密等级">
                            <Select options={confidentialityOptions} />
                          </Form.Item>
                          <Form.Item name="ai_usage_policy" label="文件 AI 使用规则">
                            <Select options={aiUsagePolicyOptions} />
                          </Form.Item>
                          <Form.Item name="ai_enabled" label="文件 AI 开关">
                            <Select options={[{ label: '启用', value: 'true' }, { label: '禁用', value: 'false' }]} />
                          </Form.Item>
                          <Form.Item name="maintainer_id" label="文件维护人">
                            <Select allowClear showSearch optionFilterProp="label" options={userOptions} />
                          </Form.Item>
                          <Form.Item name="expires_at" label="文件有效期">
                            <Input type="date" placeholder="为空表示长期有效" />
                          </Form.Item>
                        </div>
                        <Button htmlType="submit" loading={loading}>保存文件设置</Button>
                      </Form>
                    </Space>
                  </Card>
                )}

                <Form form={folderForm} layout="inline" className="responsive-inline-form" onFinish={createFolder}>
                  <Form.Item name="name" rules={[{ required: true, message: '请输入文件夹名称' }]}> 
                    <Input disabled={!canCreateInCurrentLocation} placeholder="新文件夹名称" style={{ width: 240 }} />
                  </Form.Item>
                  <Button htmlType="submit" disabled={!canCreateInCurrentLocation} loading={loading}>新建文件夹</Button>
                </Form>

                <Form form={textFileForm} layout="vertical" onFinish={createTextFile}>
                  <div className="knowledge-text-file-grid">
                    <Form.Item name="file_name" label="新建文件" rules={[{ required: true, message: '请输入文件名' }]}>
                      <Input disabled={!canCreateInCurrentLocation} placeholder="例如：学习笔记.md" />
                    </Form.Item>
                    <Form.Item name="content" label="文件内容" rules={[{ required: true, message: '请输入文件内容' }]}>
                      <Input.TextArea disabled={!canCreateInCurrentLocation} placeholder="在这里输入文本内容，会作为文件写入当前知识库目录" autoSize={{ minRows: 3, maxRows: 8 }} />
                    </Form.Item>
                  </div>
                  <Button htmlType="submit" disabled={!canCreateInCurrentLocation} loading={loading}>创建文本文件</Button>
                </Form>

                <div className="file-upload-row">
                  <label htmlFor="knowledge-file-upload" className="file-input-label">上传本地文件</label>
                  <input key={fileInputVersion} id="knowledge-file-upload" type="file" disabled={!canCreateInCurrentLocation} onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
                  {file && <Typography.Text type="secondary">已选择：{file.name}（{Math.ceil(file.size / 1024)} KB）</Typography.Text>}
                  <Button type="primary" disabled={!file || !canCreateInCurrentLocation} loading={loading} onClick={uploadFile}>上传到当前位置</Button>
                </div>

                <Table
                  rowKey="id"
                  title={() => '当前知识库文件夹'}
                  dataSource={activeTree?.folders ?? []}
                  pagination={false}
                  scroll={{ x: 720 }}
                  rowClassName={(record) => record.id === selectedFolder?.id ? 'knowledge-selectable-row is-selected' : 'knowledge-selectable-row'}
                  onRow={(record) => ({
                    onClick: () => {
                      if (!activeKnowledgeBaseId) return;
                      setSelectedId(activeKnowledgeBaseId);
                      setSelectedKey(folderKey(record.id));
                    }
                  })}
                  columns={[
                    { title: '名称', dataIndex: 'name', ellipsis: true },
                    { title: '状态', dataIndex: 'status', render: (status) => <Tag>{status}</Tag> },
                    { title: '父文件夹', dataIndex: 'parent_id', ellipsis: true, render: (value) => findFolder(activeTree, value)?.name ?? '-' }
                  ]}
                />
                <Table
                  rowKey="id"
                  title={() => '当前知识库文件'}
                  dataSource={activeTree?.files ?? []}
                  pagination={{ pageSize: 10 }}
                  scroll={{ x: 820 }}
                  rowClassName={(record) => record.id === selectedFile?.id ? 'knowledge-selectable-row is-selected' : 'knowledge-selectable-row'}
                  onRow={(record) => ({
                    onClick: () => {
                      if (!activeKnowledgeBaseId) return;
                      setSelectedId(activeKnowledgeBaseId);
                      setSelectedKey(fileKey(record.id));
                    }
                  })}
                  columns={[
                    { title: '文件名', dataIndex: 'file_name', ellipsis: true },
                    { title: '类型', dataIndex: 'file_ext', render: (value) => value || '-' },
                    { title: '所在文件夹', dataIndex: 'folder_id', ellipsis: true, render: (value) => findFolder(activeTree, value)?.name ?? '根目录' },
                    { title: '处理状态', dataIndex: 'process_status', render: (status) => <Tag color={status === 'ai_disabled' ? 'red' : undefined}>{status}</Tag> },
                    { title: '高敏', dataIndex: 'is_high_sensitive', render: (value) => value ? <Tag color="red">高敏</Tag> : '-' },
                    { title: '审核状态', dataIndex: 'review_status', render: (value) => <Tag>{reviewStatusLabels[String(value)] ?? value}</Tag> },
                    { title: 'AI 规则', dataIndex: 'ai_usage_policy', render: (value) => aiUsagePolicyLabels[String(value)] ?? value }
                  ]}
                />

                <Card size="small" title="回收站" extra={<Button size="small" loading={trashLoading} disabled={!activeKnowledgeBaseId || !canManageTrash} onClick={() => activeKnowledgeBaseId && loadTrashTree(activeKnowledgeBaseId).catch((error) => message.warning(error.message || '回收站加载失败'))}>刷新</Button>}>
                  <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                    {canManageTrash ? (
                      <Alert
                        type="info"
                        showIcon
                        message="软删除文件和文件夹可在这里恢复"
                        description="恢复文件夹会同时恢复其子文件夹和子文件；上级文件夹仍在回收站时，请先恢复上级文件夹。"
                      />
                    ) : (
                      <Alert type="warning" showIcon message="当前角色无权查看回收站" description="只有管理员或编辑者可以查看并恢复软删除内容。" />
                    )}
                    <Table
                      rowKey="id"
                      size="small"
                      title={() => `已删除文件夹（${deletedFolders.length}）`}
                      dataSource={deletedFolders}
                      pagination={false}
                      locale={{ emptyText: <Empty description="暂无已删除文件夹" /> }}
                      scroll={{ x: 760 }}
                      columns={[
                        { title: '名称', dataIndex: 'name', ellipsis: true },
                        { title: '原父级', dataIndex: 'parent_id', ellipsis: true, render: (value) => value ? findFolder(activeTrashTree, value)?.name ?? value : '根目录' },
                        { title: '删除时间', dataIndex: 'deleted_at', render: formatTime },
                        {
                          title: '操作',
                          render: (_, record) => {
                            const parentDeleted = record.parent_id ? deletedFolderIds.has(record.parent_id) : false;
                            return (
                              <Button size="small" loading={trashLoading} disabled={parentDeleted} onClick={() => restoreDeletedFolder(record.id)}>
                                {parentDeleted ? '先恢复上级' : '恢复文件夹'}
                              </Button>
                            );
                          }
                        }
                      ]}
                    />
                    <Table
                      rowKey="id"
                      size="small"
                      title={() => `已删除文件（${deletedFiles.length}）`}
                      dataSource={deletedFiles}
                      pagination={{ pageSize: 5 }}
                      locale={{ emptyText: <Empty description="暂无已删除文件" /> }}
                      scroll={{ x: 820 }}
                      columns={[
                        { title: '文件名', dataIndex: 'file_name', ellipsis: true },
                        { title: '原文件夹', dataIndex: 'folder_id', ellipsis: true, render: (value) => value ? findFolder(activeTrashTree, value)?.name ?? value : '根目录' },
                        { title: '删除时间', dataIndex: 'deleted_at', render: formatTime },
                        {
                          title: '操作',
                          render: (_, record) => {
                            const parentDeleted = record.folder_id ? deletedFolderIds.has(record.folder_id) : false;
                            return (
                              <Button size="small" loading={trashLoading} disabled={parentDeleted} onClick={() => restoreDeletedFile(record.id)}>
                                {parentDeleted ? '先恢复文件夹' : '恢复文件'}
                              </Button>
                            );
                          }
                        }
                      ]}
                    />
                  </Space>
                </Card>

              </Space>
            ) : (
              <Empty description="请选择左侧知识库，或先创建一个知识库" />
            )}
          </Card>
        </Space>

        <KnowledgeBaseChatPanel knowledgeBaseId={activeKnowledgeBaseId} knowledgeBase={selected} currentFile={selectedFile} onOpenCitationFile={openCitationFile} />

      <Modal
        title={`新建${quickCreateType ? typeLabels[quickCreateType] : '知识库'}`}
        open={Boolean(quickCreateType)}
        okText="创建"
        cancelText="取消"
        confirmLoading={loading}
        onCancel={() => setQuickCreateType(undefined)}
        onOk={() => quickCreateForm.submit()}
      >
        <Form
          form={quickCreateForm}
          layout="vertical"
          onFinish={createQuickKnowledgeBase}
          initialValues={{ knowledge_type: 'general', review_status: 'published', confidentiality_level: 'internal', ai_usage_policy: 'allow_generation', ai_enabled: 'true', citation_priority: 0 }}
        >
          <Form.Item name="name" label="知识库名称" rules={[{ required: true, message: '请输入知识库名称' }]}> 
            <Input autoFocus placeholder={quickCreateType === 'team' ? '例如：团队知识库' : '例如：个人笔记'} />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea placeholder="可选，用于说明这个知识库放什么内容" autoSize={{ minRows: 3, maxRows: 5 }} />
          </Form.Item>
          <div className="knowledge-governance-grid">
            <Form.Item name="knowledge_type" label="知识类型">
              <Select options={knowledgeTypeOptions} />
            </Form.Item>
            <Form.Item name="review_status" label="审核状态">
              <Select options={reviewStatusOptions} />
            </Form.Item>
            <Form.Item name="confidentiality_level" label="保密等级">
              <Select options={confidentialityOptions} />
            </Form.Item>
            <Form.Item name="ai_usage_policy" label="AI 使用规则">
              <Select options={aiUsagePolicyOptions} />
            </Form.Item>
            <Form.Item name="ai_enabled" label="AI 开关">
              <Select options={[{ label: '启用', value: 'true' }, { label: '禁用', value: 'false' }]} />
            </Form.Item>
            <Form.Item name="maintainer_id" label="维护人">
              <Select allowClear showSearch optionFilterProp="label" options={userOptions} />
            </Form.Item>
            <Form.Item name="expires_at" label="有效期">
              <Input type="date" />
            </Form.Item>
            <Form.Item name="citation_priority" label="引用优先级">
              <Input type="number" />
            </Form.Item>
          </div>
        </Form>
      </Modal>
    </div>
  );
}
