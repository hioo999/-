import { useState } from 'react';
import { Button, Card, Form, Input, Typography, message } from 'antd';
import { agentClient } from '../services/agentClient';
import { setToken } from '../services/tokenStore';
import type { LocalUser } from '../types/api';

export function LoginPage({ onLoggedIn }: { onLoggedIn: (user: LocalUser) => void }) {
  const [loading, setLoading] = useState(false);

  return (
    <div className="login-shell">
      <Card title="Agent 本地登录" className="login-card">
        <Typography.Paragraph type="secondary">登录后才能访问本地知识库、文件和问答能力。</Typography.Paragraph>
        <Form
          layout="vertical"
          onFinish={async (values) => {
            setLoading(true);
            try {
              const result = await agentClient.login(values.account, values.password);
              setToken(result.token);
              onLoggedIn(result.user);
            } catch (error) {
              message.error((error as Error).message);
            } finally {
              setLoading(false);
            }
          }}
        >
          <Form.Item label="账号" name="account" rules={[{ required: true }]}>
            <Input autoComplete="username" />
          </Form.Item>
          <Form.Item label="密码" name="password" rules={[{ required: true }]}>
            <Input.Password autoComplete="current-password" />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={loading} block>登录</Button>
        </Form>
      </Card>
    </div>
  );
}
