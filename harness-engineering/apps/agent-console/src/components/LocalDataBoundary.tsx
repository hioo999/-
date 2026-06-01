import { Alert, Card, Space, Tag, Typography } from 'antd';

const boundaryItems = [
  {
    title: '业务数据本地处理',
    description: '知识库文件、文件正文、RAG 上下文和 Prompt 只进入本地 Agent。',
    tag: 'Local'
  },
  {
    title: '平台不可见知识内容',
    description: '平台端只接收脱敏健康状态，不接收知识库名称、正文、问答或引用内容。',
    tag: 'Redacted'
  },
  {
    title: '凭证本地保存',
    description: '模型 Base URL 与 API Key 由本地保存，接口响应只返回遮罩后的 Key 状态。',
    tag: 'Private'
  }
];

export function LocalDataBoundaryBanner() {
  return (
    <Alert
      type="success"
      showIcon
      message="当前页面运行在本地 Agent"
      description="知识库、文件、问答、Prompt、模型 API Key 仅在本地处理，平台不可见。"
    />
  );
}

export function LocalDataBoundaryCard() {
  return (
    <Card title="本地数据边界" className="trust-card">
      <div className="trust-grid">
        {boundaryItems.map((item) => (
          <div key={item.title}>
            <Space wrap>
              <Typography.Text strong>{item.title}</Typography.Text>
              <Tag color="blue">{item.tag}</Tag>
            </Space>
            <Typography.Paragraph type="secondary">{item.description}</Typography.Paragraph>
          </div>
        ))}
      </div>
    </Card>
  );
}
