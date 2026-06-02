import { useEffect, useState } from 'react';
import { Button, Card, Space, Table, Tag, message } from 'antd';
import { agentClient } from '../services/agentClient';
import type { ProcessingTask } from '../types/api';

export function TasksPage() {
  const [tasks, setTasks] = useState<ProcessingTask[]>([]);
  const [loading, setLoading] = useState(false);

  const loadTasks = async () => {
    setLoading(true);
    try {
      setTasks(await agentClient.tasks());
    } catch (error) {
      message.warning((error as Error).message || '任务列表加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadTasks();
  }, []);

  return (
    <Card title="处理任务" extra={<Button onClick={() => void loadTasks()}>刷新</Button>}>
      <Space direction="vertical" size={12} className="full-width-stack">
        <Table
          rowKey="id"
          loading={loading}
          dataSource={tasks}
          columns={[
            { title: '任务类型', dataIndex: 'task_type' },
            { title: '状态', dataIndex: 'status', render: (status) => <Tag>{status}</Tag> },
            { title: '重试次数', dataIndex: 'retry_count' },
            { title: '错误码', dataIndex: 'error_code', render: (value) => value ?? '-' }
          ]}
          pagination={{ pageSize: 10 }}
        />
      </Space>
    </Card>
  );
}
