import { Suspense, lazy, type ReactNode } from 'react';
import { Card, Spin } from 'antd';

const DataSourcesPage = lazy(() => import('../pages/DataSourcesPage').then((module) => ({ default: module.DataSourcesPage })));
const KnowledgeBasesPage = lazy(() => import('../pages/KnowledgeBasesPage').then((module) => ({ default: module.KnowledgeBasesPage })));
const ModelConfigPage = lazy(() => import('../pages/ModelConfigPage').then((module) => ({ default: module.ModelConfigPage })));

export type RouteKey = 'knowledge-bases' | 'sources' | 'models';

export function renderRoute(
  route: RouteKey,
  selectedKnowledgeBaseId?: string,
  refreshKnowledgeBases?: () => Promise<unknown>,
  onSelectKnowledgeBase?: (knowledgeBaseId: string | undefined) => void
): ReactNode {
  let page: ReactNode = <KnowledgeBasesPage initialKnowledgeBaseId={selectedKnowledgeBaseId} onKnowledgeBasesChanged={refreshKnowledgeBases} onSelectKnowledgeBase={onSelectKnowledgeBase} />;
  if (route === 'sources') page = <DataSourcesPage knowledgeBaseId={selectedKnowledgeBaseId} />;
  if (route === 'models') page = <ModelConfigPage />;

  return (
    <Suspense fallback={<Card><Spin /> 正在加载知识库工作台...</Card>}>
      {page}
    </Suspense>
  );
}
