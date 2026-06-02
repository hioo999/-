import { Alert, Card, List, Space, Tag, Typography } from 'antd';

const deliveryArtifacts = [
  'harness-engineering-delivery.tar.gz',
  'harness-engineering-delivery.tar.gz.sha256',
  'delivery-acceptance-report.json',
  'delivery-bundle-manifest.json'
];

const verificationSteps = [
  '执行 bash scripts/verify-mvp.sh 完成 MVP 回归、平台不可见报告、交付包边界和泄漏扫描',
  '使用一键导出交付 bundle 生成可复验交付目录',
  '复验完整 bundle，确认验收报告、manifest 和 checksum 一致',
  '确认报告为 metadata-only，不展示案件、文件正文、问答正文、Prompt、向量或模型密钥'
];

const p0EvidenceItems = [
  'knowledge_governance_metadata_and_audit',
  'ai_risk_controls_and_policy_enforcement',
  'quality_feedback_closed_loop',
  'historical_citation_and_source_traceability',
  'platform_invisibility_special_checks',
  'delivery_acceptance_package_redaction'
];

export function DeliveryAcceptancePage() {
  return (
    <Space direction="vertical" size={16} className="full-width-stack">
      <Alert
        type="success"
        showIcon
        message="交付验收坚持 metadata-only 与平台不可见"
        description="本页面只展示交付检查口径和证据项名称，不展示案件、文件正文、问答正文、Prompt、向量或模型密钥。"
      />

      <Card title="V5 P0 交付验收包">
        <Typography.Paragraph>
          交付验收以本地 Agent 可复验为准，客户可在解包目录执行 <Typography.Text code>bash scripts/verify-mvp.sh</Typography.Text> 完成基础复验。
        </Typography.Paragraph>
        <Space wrap>
          <Tag color="green">平台不可见</Tag>
          <Tag color="blue">metadata-only</Tag>
          <Tag color="purple">不展示案件</Tag>
          <Tag color="gold">V5 P0 专项证据</Tag>
        </Space>
      </Card>

      <Card title="一键导出交付 bundle">
        <List
          dataSource={deliveryArtifacts}
          renderItem={(item) => (
            <List.Item>
              <Typography.Text code>{item}</Typography.Text>
            </List.Item>
          )}
        />
      </Card>

      <Card title="复验完整 bundle">
        <List
          dataSource={verificationSteps}
          renderItem={(item) => <List.Item>{item}</List.Item>}
        />
      </Card>

      <Card title="V5 P0 专项证据摘要">
        <List
          dataSource={p0EvidenceItems}
          renderItem={(item) => (
            <List.Item>
              <Typography.Text code>{item}</Typography.Text>
            </List.Item>
          )}
        />
      </Card>
    </Space>
  );
}
