import { Alert, Card, Typography } from 'antd';

export function RagChatPage() {
  return (
    <Card title="RAG 问答">
      <Alert
        type="info"
        showIcon
        message="RAG 问答已并入知识库工作台"
        description="当前版本优先在三栏式知识库工作台中完成资料定位、AI 问答、来源引用、拒答提示和质量反馈。"
      />
      <Typography.Paragraph style={{ marginTop: 16 }}>
        法律 AI 回答必须可核验、可追溯；证据不足时应明确提示，不输出无依据的确定性结论。
      </Typography.Paragraph>
    </Card>
  );
}
