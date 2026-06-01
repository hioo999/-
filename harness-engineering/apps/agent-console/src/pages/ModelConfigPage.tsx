import { useEffect, useState } from 'react';
import { Alert, Button, Card, Form, Input, Space, Table, Tag, Typography, message } from 'antd';
import { agentClient } from '../services/agentClient';
import type { ModelConfig, ModelConnectivityResult } from '../types/api';

export function ModelConfigPage() {
  const [configs, setConfigs] = useState<ModelConfig[]>([]);
  const [testResult, setTestResult] = useState<ModelConnectivityResult | null>(null);
  const [loading, setLoading] = useState(false);

  const loadConfigs = () => agentClient.modelConfigs().then(setConfigs).catch((error) => message.error(error.message));

  useEffect(() => {
    loadConfigs();
  }, []);

  const saveConfig = async (values: Record<string, string>) => {
    setLoading(true);
    try {
      await agentClient.saveModelConfig(values);
      message.success('模型配置已本地保存');
      await loadConfigs();
    } finally {
      setLoading(false);
    }
  };

  const testConfig = async (configId: string, mode: 'chat' | 'embedding') => {
    setLoading(true);
    try {
      const result = await agentClient.testModelConfig(configId, mode);
      setTestResult(result);
      if (result.status === 'success') {
        message.success(`${mode} 连通性测试成功`);
      } else {
        message.warning(`${mode} 连通性测试失败：${result.error_code ?? result.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Card title="模型配置">
        <Typography.Paragraph type="secondary">API Key 仅本地保存，接口响应只返回遮罩。连通性测试由本地 Agent 直接访问模型服务。</Typography.Paragraph>
        <Form layout="vertical" onFinish={saveConfig}>
          <Form.Item label="Provider" name="provider" initialValue="openai-compatible"><Input /></Form.Item>
          <Form.Item label="Base URL" name="base_url" rules={[{ required: true }]}><Input placeholder="http://127.0.0.1:11434/v1" /></Form.Item>
          <Form.Item label="Chat Model" name="chat_model" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item label="Embedding Model" name="embedding_model" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item label="API Key" name="api_key" rules={[{ required: true }]}><Input.Password /></Form.Item>
          <Button type="primary" htmlType="submit" loading={loading}>保存配置</Button>
        </Form>
      </Card>

      <Card title="已保存配置">
        <Table
          rowKey="id"
          dataSource={configs}
          pagination={{ pageSize: 10 }}
          scroll={{ x: 960 }}
          columns={[
            { title: 'Provider', dataIndex: 'provider' },
            { title: 'Base URL', dataIndex: 'base_url', ellipsis: true },
            { title: 'Chat', dataIndex: 'chat_model', ellipsis: true },
            { title: 'Embedding', dataIndex: 'embedding_model', ellipsis: true },
            { title: 'Key', dataIndex: 'api_key_masked' },
            { title: '状态', dataIndex: 'status', render: (status) => <Tag>{status}</Tag> },
            {
              title: '连通性',
              render: (_, record) => (
                <Space>
                  <Button size="small" loading={loading} onClick={() => testConfig(record.id, 'chat')}>测 Chat</Button>
                  <Button size="small" loading={loading} onClick={() => testConfig(record.id, 'embedding')}>测 Embedding</Button>
                </Space>
              )
            }
          ]}
        />
      </Card>

      {testResult && (
        <Alert
          type={testResult.status === 'success' ? 'success' : 'warning'}
          showIcon
          message={`${testResult.mode}：${testResult.status}`}
          description={`${testResult.message}，耗时 ${testResult.latency_ms}ms${testResult.error_code ? `，错误码 ${testResult.error_code}` : ''}`}
        />
      )}
    </Space>
  );
}
