import { useEffect, useState } from 'react';
import { Card, Table, Tag, message } from 'antd';
import { agentClient } from '../services/agentClient';
import type { CaseSpace } from '../types/api';

export function CasesPage() {
  const [cases, setCases] = useState<CaseSpace[]>([]);

  useEffect(() => {
    agentClient.cases()
      .then(setCases)
      .catch((error) => message.warning((error as Error).message || '案件列表加载失败'));
  }, []);

  return (
    <Card title="案件空间">
      <Table
        rowKey="id"
        dataSource={cases}
        columns={[
          { title: '案件标题', dataIndex: 'title' },
          { title: '案由', dataIndex: 'cause_of_action', render: (value) => value ?? '-' },
          { title: '阶段', dataIndex: 'stage', render: (value) => value ?? '-' },
          { title: '状态', dataIndex: 'status', render: (status) => <Tag>{status}</Tag> }
        ]}
      />
    </Card>
  );
}
