import { useEffect, useState } from 'react';
import { Alert, Button, Card, Empty, Form, Input, Space, Table, Tag, Typography, message } from 'antd';
import { agentClient } from '../services/agentClient';
import type { DirectoryPermission, LocalDataSource, ScanResult } from '../types/api';

export function DataSourcesPage({ knowledgeBaseId }: { knowledgeBaseId?: string }) {
  const [sources, setSources] = useState<LocalDataSource[]>([]);
  const [permission, setPermission] = useState<DirectoryPermission | null>(null);
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [sourceQuery, setSourceQuery] = useState('');
  const filteredSources = sources.filter((source) => `${source.path} ${source.status} ${source.permission_status}`.toLowerCase().includes(sourceQuery.trim().toLowerCase()));

  const loadSources = () => agentClient.dataSources().then(setSources).catch((error) => message.error(error.message));

  useEffect(() => {
    loadSources();
  }, []);

  const checkPermission = async (values: { path: string }) => {
    const result = await agentClient.checkDirectory(values.path);
    setPermission(result);
  };

  const addSource = async (path: string) => {
    setLoading(true);
    try {
      await agentClient.addDataSource(path);
      message.success('目录已加入本地 Agent');
      await loadSources();
    } finally {
      setLoading(false);
    }
  };

  const scanSource = async (sourceId: string) => {
    if (!knowledgeBaseId) {
      message.warning('请先在左侧选择一个知识库，再扫描目录入库');
      return;
    }
    setLoading(true);
    try {
      const result = await agentClient.scanDataSource(sourceId, undefined, knowledgeBaseId);
      setScanResult(result);
      message.success(`扫描完成，新增 ${result.added_count} 个文件，入队 ${result.enqueued_count} 个任务`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Card title="本地目录配置">
        <Typography.Paragraph type="secondary">目录路径只发送给本地 Agent，不会上报平台。新增目录要求路径已存在且可读。</Typography.Paragraph>
        {!knowledgeBaseId && <Alert type="warning" showIcon message="尚未选择知识库，目录可配置但不能扫描入库。" style={{ marginBottom: 16 }} />}
        <Form layout="inline" className="responsive-inline-form" onFinish={checkPermission}>
          <Form.Item name="path" rules={[{ required: true }]}> 
            <Input placeholder="/data/knowledge" style={{ width: 360 }} />
          </Form.Item>
          <Button htmlType="submit">检查权限</Button>
          {permission?.readable && <Button loading={loading} onClick={() => addSource(permission.path)}>加入目录</Button>}
        </Form>
        {permission && (
          <Alert
            style={{ marginTop: 16 }}
            type={permission.readable ? 'success' : 'error'}
            showIcon
            message={`${permission.path}：${permission.permission_status}`}
            description={`存在：${permission.exists ? '是' : '否'}，目录：${permission.is_dir ? '是' : '否'}，可读：${permission.readable ? '是' : '否'}，可写：${permission.writable ? '是' : '否'}`}
          />
        )}
      </Card>

      <Card
        title="已配置目录"
        extra={<Input.Search allowClear placeholder="搜索路径/状态" value={sourceQuery} onChange={(event) => setSourceQuery(event.target.value)} />}
      >
        <Table
          rowKey="id"
          dataSource={filteredSources}
          locale={{ emptyText: <Empty description="没有匹配的本地目录" /> }}
          loading={loading}
          pagination={{ pageSize: 10 }}
          scroll={{ x: 860 }}
          columns={[
            { title: '路径', dataIndex: 'path', ellipsis: true },
            { title: '状态', dataIndex: 'status', render: (status) => <Tag>{status}</Tag> },
            { title: '权限', dataIndex: 'permission_status' },
            { title: '操作', render: (_, record) => <Button disabled={!knowledgeBaseId} onClick={() => scanSource(record.id)}>扫描入库</Button> }
          ]}
        />
      </Card>

      {scanResult && (
        <Alert
          type="success"
          showIcon
          message="最近一次扫描结果"
          description={`发现 ${scanResult.discovered_count}，新增 ${scanResult.added_count}，重复 ${scanResult.duplicate_count}，不支持 ${scanResult.unsupported_count}，入队 ${scanResult.enqueued_count}，错误 ${scanResult.error_count}`}
        />
      )}
    </Space>
  );
}
