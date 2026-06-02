import { useEffect, useState } from 'react';
import { Alert, Card, Space, message } from 'antd';
import { StatusCard } from '../components/StatusCard';
import { agentClient } from '../services/agentClient';
import type { AgentStatus } from '../types/api';

export function AgentStatusPage() {
  const [status, setStatus] = useState<AgentStatus>();

  useEffect(() => {
    agentClient.status()
      .then(setStatus)
      .catch((error) => message.warning((error as Error).message || 'Agent 状态加载失败'));
  }, []);

  return (
    <Space direction="vertical" size={16} className="full-width-stack">
      <Alert type="info" showIcon message="Agent 状态" description="仅展示本地 Agent 运行状态和脱敏健康信息，平台不可见律师业务数据。" />
      <StatusCard status={status} />
      <Card title="本地运行边界">文件、问答、向量、Prompt 和模型密钥只在本地 Agent 处理。</Card>
    </Space>
  );
}
