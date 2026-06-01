import { Card, Descriptions, Tag } from 'antd';
import type { AgentStatus } from '../types/api';

function statusTag(value?: string) {
  if (!value || value === 'unknown') return <Tag color="default">未知</Tag>;
  if (['ok', 'success', 'healthy', 'active'].includes(value)) return <Tag color="green">正常</Tag>;
  if (['not_configured', 'missing'].includes(value)) return <Tag color="gold">待配置</Tag>;
  return <Tag color="red">需处理：{value}</Tag>;
}

export function StatusCard({ status }: { status?: AgentStatus }) {
  return (
    <Card title="Agent 状态">
      <Descriptions column={1} size="small">
        <Descriptions.Item label="API">{statusTag(status?.api)}</Descriptions.Item>
        <Descriptions.Item label="数据库">{statusTag(status?.database)}</Descriptions.Item>
        <Descriptions.Item label="文件存储">{statusTag(status?.storage)}</Descriptions.Item>
        <Descriptions.Item label="任务队列">{status?.task_queue ?? '-'}</Descriptions.Item>
        <Descriptions.Item label="向量库">{status?.vector_store ?? '-'}</Descriptions.Item>
        <Descriptions.Item label="本地向量数">{status?.embedding_vector_count ?? 0}</Descriptions.Item>
        <Descriptions.Item label="Qdrant 配置">{status?.qdrant_configured ? '已配置' : '未配置'}</Descriptions.Item>
        <Descriptions.Item label="OCR 配置">{status?.ocr_configured ? '已配置' : '未配置'}</Descriptions.Item>
        <Descriptions.Item label="模型配置">{statusTag(status?.model_connectivity)}</Descriptions.Item>
      </Descriptions>
    </Card>
  );
}
