import { useEffect, useState } from 'react';
import { Button, Card, Drawer, Dropdown, Layout, Menu, Space, Typography, message } from 'antd';
import type { MenuProps } from 'antd';
import { LocalOnlyBanner } from './components/LocalOnlyBanner';
import { LoginPage } from './pages/LoginPage';
import { SetupPage } from './pages/SetupPage';
import { agentClient } from './services/agentClient';
import { clearToken, getToken } from './services/tokenStore';
import { renderRoute, type RouteKey } from './routes';
import type { KnowledgeBase, LocalUser } from './types/api';

const knowledgeBaseMenuKey = (knowledgeBaseId: string) => `knowledge-base:${knowledgeBaseId}`;
const knowledgeBaseMenuKeyPrefix = 'knowledge-base:';

const knowledgeBaseTypeLabels: Record<KnowledgeBase['type'], string> = {
  private: '个人知识库',
  team: '共享知识库',
  case: '归档知识库'
};

function isKnowledgeBaseMenuKey(value: string) {
  return value.startsWith(knowledgeBaseMenuKeyPrefix);
}

function buildKnowledgeBaseMenuGroup(type: KnowledgeBase['type'], knowledgeBases: KnowledgeBase[]) {
  const items = knowledgeBases.filter((item) => item.type === type);
  return {
    type: 'group' as const,
    key: `knowledge-category:${type}`,
    label: `${knowledgeBaseTypeLabels[type]}（${items.length}）`,
    children: items.length
      ? items.map((item) => ({ key: knowledgeBaseMenuKey(item.id), label: item.name }))
      : [{ key: `knowledge-empty:${type}`, label: '暂无知识库', disabled: true }]
  };
}

function buildMenuItems(knowledgeBases: KnowledgeBase[]): MenuProps['items'] {
  return [
    {
      type: 'group',
      label: '知识库',
      children: [
      {
        key: 'knowledge-menu',
        label: '知识库工作台',
        children: [
          { key: 'knowledge-bases', label: '打开工作台' },
          { type: 'divider' },
          buildKnowledgeBaseMenuGroup('private', knowledgeBases),
          buildKnowledgeBaseMenuGroup('team', knowledgeBases)
        ]
      },
      { key: 'sources', label: '本地目录' }
      ]
    },
    {
      type: 'group',
      label: '设置',
      children: [
      { key: 'models', label: '模型配置' },
      { key: 'delivery', label: '交付验收' }
      ]
    }
  ];
}

const routeLabels: Record<RouteKey, string> = {
  'knowledge-bases': '知识库工作台',
  sources: '本地目录',
  models: '模型配置',
  delivery: '交付验收'
};

const routeKeys = new Set<RouteKey>(Object.keys(routeLabels) as RouteKey[]);

function isRouteKey(value: string): value is RouteKey {
  return routeKeys.has(value as RouteKey);
}

function buildHash(route: RouteKey, knowledgeBaseId?: string) {
  const params = new URLSearchParams();
  if (knowledgeBaseId) params.set('knowledge_base', knowledgeBaseId);
  const query = params.toString();
  return `#/${route}${query ? `?${query}` : ''}`;
}

function parseHash(): { route: RouteKey; knowledgeBaseId?: string } {
  const raw = window.location.hash.replace(/^#\/?/, '');
  const [path = '', query = ''] = raw.split('?');
  const route = isRouteKey(path) ? path : 'knowledge-bases';
  const params = new URLSearchParams(query);
  return { route, knowledgeBaseId: params.get('knowledge_base') ?? undefined };
}

export function App() {
  const [authenticated, setAuthenticated] = useState(Boolean(getToken()));
  const [setupRequired, setSetupRequired] = useState(false);
  const [checkingSetup, setCheckingSetup] = useState(true);
  const [initialRoute] = useState(parseHash);
  const [route, setRoute] = useState<RouteKey>(initialRoute.route);
  const [selectedKnowledgeBaseId, setSelectedKnowledgeBaseId] = useState<string | undefined>(initialRoute.knowledgeBaseId);
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [user, setUser] = useState<LocalUser>();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const menuItems = buildMenuItems(knowledgeBases);
  const selectedMenuKeys = route === 'knowledge-bases' && selectedKnowledgeBaseId ? [knowledgeBaseMenuKey(selectedKnowledgeBaseId)] : [route];
  const showGlobalSider = route !== 'knowledge-bases';

  const refreshKnowledgeBases = async () => {
    const nextKnowledgeBases = await agentClient.knowledgeBases();
    setKnowledgeBases(nextKnowledgeBases);
    setSelectedKnowledgeBaseId((current) => (current && nextKnowledgeBases.some((item) => item.id === current) ? current : undefined));
    return nextKnowledgeBases;
  };

  useEffect(() => {
    const handleHashChange = () => {
      const next = parseHash();
      setRoute(next.route);
      setSelectedKnowledgeBaseId(next.knowledgeBaseId);
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  useEffect(() => {
    let active = true;
    agentClient.setupStatus()
      .then((status) => {
        if (!active) return;
        setSetupRequired(status.setup_required);
        if (status.setup_required) {
          clearToken();
          setAuthenticated(false);
        }
      })
      .catch(() => {
        if (active) setSetupRequired(false);
      })
      .finally(() => {
        if (active) setCheckingSetup(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!authenticated) return;
    let active = true;
    agentClient.me()
      .then((currentUser) => {
        if (active) setUser(currentUser);
      })
      .catch((error) => {
        if (!active) return;
        clearToken();
        setUser(undefined);
        setAuthenticated(false);
        message.warning(error.message || '登录状态已失效，请重新登录');
      });
    refreshKnowledgeBases().catch((error) => {
      if (active) message.warning(error.message || '知识库列表加载失败');
    });
    return () => {
      active = false;
    };
  }, [authenticated]);

  const handleLogout = async () => {
    try {
      await agentClient.logout();
    } catch {
      // Local cleanup still protects the console if the server session is already expired.
    }
    clearToken();
    setUser(undefined);
    setAuthenticated(false);
    setRoute('knowledge-bases');
    setSelectedKnowledgeBaseId(undefined);
    setKnowledgeBases([]);
    window.history.replaceState(null, '', buildHash('knowledge-bases'));
    message.success('已退出登录');
  };

  const navigateTo = (nextRoute: RouteKey) => {
    setRoute(nextRoute);
    setMobileMenuOpen(false);
    window.location.hash = buildHash(nextRoute, selectedKnowledgeBaseId);
  };

  const navigateToKnowledgeBaseManager = (knowledgeBaseId: string) => {
    setRoute('knowledge-bases');
    setSelectedKnowledgeBaseId(knowledgeBaseId);
    setMobileMenuOpen(false);
    window.location.hash = buildHash('knowledge-bases', knowledgeBaseId);
  };

  const selectKnowledgeBase = (knowledgeBaseId: string | undefined) => {
    setSelectedKnowledgeBaseId(knowledgeBaseId);
    if (route === 'knowledge-bases') {
      window.history.replaceState(null, '', buildHash('knowledge-bases', knowledgeBaseId));
    }
  };

  const handleMenuClick: MenuProps['onClick'] = (item) => {
    const key = String(item.key);
    if (isKnowledgeBaseMenuKey(key)) {
      navigateToKnowledgeBaseManager(key.slice(knowledgeBaseMenuKeyPrefix.length));
      return;
    }
    if (isRouteKey(key)) navigateTo(key);
  };

  const accountMenu: MenuProps = {
    items: [
      {
        key: 'account',
        label: (
          <div className="account-menu-card">
            <Typography.Text strong>{user?.name ?? '本地管理员'}</Typography.Text>
            <Typography.Text type="secondary">账号：{user?.account ?? 'admin'}</Typography.Text>
            <Typography.Text type="secondary">角色：{user?.role ?? 'admin'}</Typography.Text>
          </div>
        )
      },
      { type: 'divider' },
      { key: 'logout', label: '退出登录', danger: true }
    ],
    onClick: ({ key }) => {
      if (key === 'logout') void handleLogout();
    }
  };

  if (!authenticated) {
    if (checkingSetup) {
      return <div className="login-shell"><Card className="login-card">正在检查本地初始化状态...</Card></div>;
    }

    if (setupRequired) {
      return <SetupPage onSetupCompleted={() => setSetupRequired(false)} />;
    }

    return <LoginPage onLoggedIn={(loggedInUser) => {
      setUser(loggedInUser);
      setAuthenticated(true);
    }} />;
  }

  return (
    <Layout className="app-shell">
      <a className="skip-link" href="#main-content">跳到主要内容</a>
      {showGlobalSider && (
        <Layout.Sider width={220} theme="light" className="desktop-sider">
          <Typography.Title level={4} className="brand">知识库工作台</Typography.Title>
          <Menu selectedKeys={selectedMenuKeys} items={menuItems} onClick={handleMenuClick} aria-label="主导航" />
        </Layout.Sider>
      )}
      <Layout>
        <Layout.Header className="topbar">
          <Space size={12} align="center">
            <Button className="mobile-menu-button" type="text" onClick={() => setMobileMenuOpen(true)} aria-label="打开主导航">菜单</Button>
            <Typography.Title level={4} className="topbar-title">{routeLabels[route]}</Typography.Title>
          </Space>
          <Dropdown menu={accountMenu} trigger={['click']} placement="bottomRight">
            <Button type="text" className="account-trigger" aria-label="打开账号菜单">
              <Space size={10}>
                <span className="account-avatar">{(user?.name ?? user?.account ?? 'A').slice(0, 1).toUpperCase()}</span>
                <span className="account-summary">
                  <Typography.Text strong>{user?.name ?? '本地管理员'}</Typography.Text>
                  <Typography.Text type="secondary">{user?.account ?? 'admin'}</Typography.Text>
                </span>
              </Space>
            </Button>
          </Dropdown>
        </Layout.Header>
        <Layout.Content id="main-content" className="content-shell" role="main">
          <LocalOnlyBanner />
          <div className="page-shell">{renderRoute(route, selectedKnowledgeBaseId, refreshKnowledgeBases, selectKnowledgeBase)}</div>
        </Layout.Content>
      </Layout>
      <Drawer title="知识库工作台导航" placement="left" open={mobileMenuOpen} onClose={() => setMobileMenuOpen(false)}>
        <Menu selectedKeys={selectedMenuKeys} defaultOpenKeys={route === 'knowledge-bases' ? ['knowledge-menu'] : undefined} items={menuItems} onClick={handleMenuClick} aria-label="移动端主导航" />
      </Drawer>
    </Layout>
  );
}
