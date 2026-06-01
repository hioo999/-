import { Button, Card, Form, Input, Typography, message } from 'antd';
import { agentClient } from '../services/agentClient';
import { clearToken } from '../services/tokenStore';

export function SetupPage({ onSetupCompleted }: { onSetupCompleted: () => void }) {
  return (
    <div className="login-shell">
      <Card title="初始化本地管理员" className="login-card">
        <Typography.Paragraph type="secondary">
          当前 Agent 仍使用默认管理员密码。首次使用前必须创建本地管理员账号，完成后旧会话会失效。
        </Typography.Paragraph>
        <Form
          layout="vertical"
          onFinish={async (values) => {
            await agentClient.setupAdmin(values);
            clearToken();
            message.success('本地管理员已初始化，请使用新账号登录');
            onSetupCompleted();
          }}
        >
          <Form.Item label="管理员账号" name="account" rules={[{ required: true }]}> 
            <Input placeholder="例如：admin" />
          </Form.Item>
          <Form.Item label="管理员姓名" name="name" rules={[{ required: true }]}> 
            <Input placeholder="例如：律所管理员" />
          </Form.Item>
          <Form.Item label="管理员密码" name="password" rules={[{ required: true, min: 8 }]}> 
            <Input.Password placeholder="至少 8 位，避免使用默认弱密码" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block>完成初始化</Button>
        </Form>
      </Card>
    </div>
  );
}
