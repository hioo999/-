import { Button, Card, Space, Tag, Typography, message } from 'antd';
import type { Citation } from '../types/api';

const { Paragraph, Text } = Typography;

const governanceFlagLabels: Record<string, string> = {
  expired: '已过期',
  needs_update: '需维护',
  deprecated: '已废止',
  search_only: '仅检索',
  ai_disabled: 'AI 禁用',
  high_sensitive: '高敏'
};

const governanceFlagColors: Record<string, string> = {
  expired: 'red',
  needs_update: 'orange',
  deprecated: 'red',
  search_only: 'gold',
  ai_disabled: 'red',
  high_sensitive: 'red'
};

const trustLevelLabels: Record<string, string> = {
  authoritative: '权威依据',
  reviewed_template: '已审模板',
  expert_experience: '专家经验',
  matter_fact: '案件事实',
  experience: '经验复盘',
  background: '背景资料',
  training: '培训材料',
  reference_only: '仅供检索',
  general: '一般资料'
};

function formatExpiry(value?: number | null) {
  return value ? new Date(value * 1000).toLocaleDateString() : undefined;
}

export function CitationCard({ citation, onOpenFile }: { citation: Citation; onOpenFile?: (citation: Citation) => void }) {
  const copyQuote = async () => {
    await navigator.clipboard.writeText(citation.quote_text);
    message.success('引用原文已复制');
  };

  return (
    <Card
      size="small"
      title={citation.file_name}
      extra={(
        <Space size="small" wrap>
          {onOpenFile && <Button size="small" type="link" onClick={() => onOpenFile(citation)}>定位文件</Button>}
          <Button size="small" onClick={copyQuote}>复制引用</Button>
        </Space>
      )}
    >
      <Space wrap size={[8, 8]}>
        <Tag color="blue">相关度 {citation.relevance_score.toFixed(2)}</Tag>
        {citation.retrieval_mode && <Tag>{citation.retrieval_mode}</Tag>}
        {citation.knowledge_trust_level && <Tag color="purple">{trustLevelLabels[citation.knowledge_trust_level] ?? citation.knowledge_trust_level}</Tag>}
        {typeof citation.citation_priority === 'number' && citation.citation_priority > 0 && <Tag>引用优先级 {citation.citation_priority}</Tag>}
        {citation.page_number && <Tag>页码 {citation.page_number}</Tag>}
        {(citation.governance_flags ?? []).map((flag) => <Tag key={flag} color={governanceFlagColors[flag] ?? 'default'}>{governanceFlagLabels[flag] ?? flag}</Tag>)}
        {citation.file_expires_at && <Tag color={citation.file_is_expired ? 'red' : undefined}>有效期 {formatExpiry(citation.file_expires_at)}</Tag>}
      </Space>
      {citation.file_requires_maintenance && (
        <div style={{ marginTop: 8 }}>
          <Text type="warning">该引用来源存在过期、需维护或废止风险，正式使用前应先复核文件治理状态。</Text>
        </div>
      )}
      <div style={{ marginTop: 8 }}>
        <Text type="secondary">chunk: {citation.chunk_id} · paragraph: {citation.paragraph_ref ?? '-'}</Text>
      </div>
      <Paragraph>{citation.quote_text}</Paragraph>
    </Card>
  );
}
