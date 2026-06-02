import { useEffect, useState } from 'react';
import { Alert, Button, Card, Empty, Form, Input, List, Modal, Select, Space, Tag, Typography, message } from 'antd';
import { agentClient } from '../services/agentClient';
import type { ChatSession, Citation, KnowledgeBase, LocalFile, RagAnswer } from '../types/api';
import { CitationCard } from './CitationCard';

type StructuredAnswerSection = {
  title: string;
  content: string;
};

const canonicalStructuredTitles = ['简要结论', '依据来源', '适用前提', '风险提示', '证据不足或需补充材料'];
const structuredTitleAliases: Record<string, string> = {
  摘要: '简要结论',
  结论: '简要结论',
  要点: '依据来源',
  依据: '依据来源',
  引用来源: '依据来源',
  适用前提: '适用前提',
  风险提示: '风险提示',
  待确认事项: '证据不足或需补充材料',
  不确定事项: '证据不足或需补充材料',
  建议下一步: '证据不足或需补充材料',
  证据不足或需补充材料: '证据不足或需补充材料'
};
const structuredSectionTitles = Object.keys(structuredTitleAliases);

const feedbackIssueOptions = [
  { label: '引用缺失', value: 'citation_missing' },
  { label: '答案不准确', value: 'answer_inaccurate' },
  { label: '证据不足', value: 'insufficient_evidence' },
  { label: '权限异常', value: 'permission_anomaly' },
  { label: '其他', value: 'other' }
];

type FeedbackValues = {
  issue_label: string;
  comment?: string;
};

function parseStructuredAnswer(answerText: string): StructuredAnswerSection[] {
  const sectionContent = new Map<string, string[]>();
  const sectionPattern = new RegExp(`(^|\\n)(${structuredSectionTitles.join('|')})：\\n`, 'g');
  const matches = Array.from(answerText.matchAll(sectionPattern));
  for (const [index, match] of matches.entries()) {
    const title = match[2];
    const canonicalTitle = structuredTitleAliases[title] ?? title;
    const start = Number(match.index) + match[0].length;
    const end = index + 1 < matches.length ? Number(matches[index + 1].index) : answerText.length;
    const content = answerText.slice(start, end).trim();
    if (content) {
      sectionContent.set(canonicalTitle, [...(sectionContent.get(canonicalTitle) ?? []), content]);
    }
  }
  const sections = canonicalStructuredTitles
    .map((title) => ({ title, content: (sectionContent.get(title) ?? []).join('\n\n') }))
    .filter((section) => section.content);
  return sections.length >= 4 ? sections : [];
}

function normalizeStructuredAnswer(sections: RagAnswer['structured_legal_answer']): StructuredAnswerSection[] {
  if (!sections?.length) return [];
  const sectionContent = new Map<string, string[]>();
  for (const section of sections) {
    const canonicalTitle = structuredTitleAliases[section.title] ?? section.title;
    if (!section.content) continue;
    sectionContent.set(canonicalTitle, [...(sectionContent.get(canonicalTitle) ?? []), section.content]);
  }
  return canonicalStructuredTitles
    .map((title) => ({ title, content: (sectionContent.get(title) ?? []).join('\n\n') }))
    .filter((section) => section.content);
}

function aiPolicyWarning(knowledgeBase?: KnowledgeBase, expired = false) {
  if (!knowledgeBase) return undefined;
  if (knowledgeBase.ai_usage_policy === 'disabled' || !knowledgeBase.ai_enabled || knowledgeBase.review_status === 'ai_disabled') {
    return '当前知识库禁止 AI 使用，后端会拒绝检索、生成或引用。';
  }
  if (knowledgeBase.ai_usage_policy === 'search_only') {
    return '当前知识库仅检索不可生成，命中材料不能用于确定性 AI 结论。';
  }
  if (expired) {
    return '当前知识库已过有效期，仍可管理和检索，但后端会拒绝生成型 AI 回答。';
  }
  return undefined;
}

export function KnowledgeBaseChatPanel({
  knowledgeBaseId,
  knowledgeBase,
  currentFile,
  onOpenCitationFile
}: {
  knowledgeBaseId?: string;
  knowledgeBase?: KnowledgeBase;
  currentFile?: LocalFile;
  onOpenCitationFile?: (citation: Citation) => void;
}) {
  const [feedbackForm] = Form.useForm<FeedbackValues>();
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState<RagAnswer>();
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<ChatSession[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyNotice, setHistoryNotice] = useState<string>();
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const knowledgeBaseExpired = Boolean(knowledgeBase?.expires_at && knowledgeBase.expires_at * 1000 <= Date.now());
  const activeScopeLabel = currentFile ? `当前文件：${currentFile.file_name}` : knowledgeBase ? `当前知识库：${knowledgeBase.name}` : '未选择上下文';
  const structuredAnswer = answer ? (answer.structured_legal_answer?.length ? normalizeStructuredAnswer(answer.structured_legal_answer) : parseStructuredAnswer(answer.answer)) : [];
  const policyWarning = aiPolicyWarning(knowledgeBase, knowledgeBaseExpired);

  const loadHistory = async (nextKnowledgeBaseId = knowledgeBaseId) => {
    if (!nextKnowledgeBaseId) {
      setHistory([]);
      return [];
    }
    setHistoryLoading(true);
    try {
      const sessions = (await agentClient.chats()).filter((item) => item.case_id === nextKnowledgeBaseId);
      setHistory(sessions);
      return sessions;
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    setAnswer(undefined);
    setHistoryNotice(undefined);
    loadHistory(knowledgeBaseId).catch((error) => message.warning(error.message || '问答历史加载失败'));
  }, [knowledgeBaseId, currentFile?.id]);

  const askQuestion = async () => {
    if ((!knowledgeBaseId && !currentFile) || !question.trim()) return;
    setLoading(true);
    try {
      const nextAnswer = currentFile
          ? await agentClient.aiQuery({ context_scope: 'current_file', file_id: currentFile.id, question: question.trim() })
          : await agentClient.aiQuery({ context_scope: 'current_knowledge_base', knowledge_base_id: String(knowledgeBaseId), question: question.trim() });
      setAnswer(nextAnswer);
      setHistoryNotice(undefined);
      await loadHistory(knowledgeBaseId);
    } catch (error) {
      setAnswer(undefined);
      message.error((error as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const restoreChat = async (sessionId: string) => {
    setHistoryLoading(true);
    try {
      const messages = await agentClient.chatMessages(sessionId);
      const lastQuestion = [...messages].reverse().find((item) => item.role === 'user');
      const lastAnswer = [...messages].reverse().find((item) => item.role === 'assistant');
      setQuestion(lastQuestion?.content ?? '');
      if (lastAnswer) {
        const restoredCitations = lastAnswer.citations ?? [];
        setAnswer({
          answer: lastAnswer.content,
          citations: restoredCitations,
          session_id: sessionId,
          message_id: lastAnswer.id,
          insufficient_evidence: lastAnswer.insufficient_evidence ?? (!lastAnswer.has_citations || restoredCitations.length === 0),
          model_status: 'history',
          model_used: undefined
        });
        setHistoryNotice(restoredCitations.length ? `已恢复历史问答，并带回 ${restoredCitations.length} 条历史引用。` : '已恢复历史问答。历史消息没有可展示引用明细，如需最新引用请重新提问。');
      }
    } catch (error) {
      message.error((error as Error).message);
    } finally {
      setHistoryLoading(false);
    }
  };

  const copyAnswer = async () => {
    if (!answer) return;
    await navigator.clipboard.writeText(answer.answer);
    message.success('回答已复制');
  };

  const submitFeedback = async (rating: 'up' | 'down', values?: FeedbackValues) => {
    if (!answer?.session_id) return;
    setFeedbackLoading(true);
    try {
      await agentClient.createAiAssistantFeedback({
        rating,
        session_id: answer.session_id,
        message_id: answer.message_id,
        issue_label: values?.issue_label ?? 'knowledge_base_chat',
        comment: values?.comment
      });
      message.success('反馈已提交');
      setFeedbackOpen(false);
      feedbackForm.resetFields();
    } catch (error) {
      message.error((error as Error).message);
    } finally {
      setFeedbackLoading(false);
    }
  };

  return (
    <Card
      title="AI 对话"
      className="knowledge-ai-card"
      extra={answer && <Button size="small" onClick={copyAnswer}>复制</Button>}
    >
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        {knowledgeBase ? (
          <Alert
            type={knowledgeBase.ai_enabled && !knowledgeBaseExpired ? 'success' : 'warning'}
            showIcon
            message={activeScopeLabel}
            description={policyWarning ?? (currentFile ? '已锁定左侧选中文件，提问会通过 /api/agent/ai/query 以 current_file 范围检索生成。' : '未选中文件时，提问会通过 /api/agent/ai/query 以 current_knowledge_base 范围检索生成。')}
          />
        ) : (
          <Alert type="info" showIcon message="请选择知识库" description="右侧对话会自动绑定左侧当前知识库。" />
        )}

        <Input.TextArea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          onPressEnter={(event) => {
            if (!event.shiftKey) {
              event.preventDefault();
              void askQuestion();
            }
          }}
          placeholder={currentFile ? '向当前文件提问，例如：总结重点、提取待办或查找关键依据' : '向当前知识库提问，例如：这份库里有哪些可复用经验？'}
          disabled={(!knowledgeBaseId && !currentFile) || loading}
          autoSize={{ minRows: 4, maxRows: 8 }}
          showCount
        />
        <Space wrap>
          <Button type="primary" disabled={(!knowledgeBaseId && !currentFile) || !question.trim()} loading={loading} onClick={askQuestion}>
            {loading ? '检索生成中' : '提问'}
          </Button>
          <Button disabled={loading || !question} onClick={() => setQuestion('')}>清空</Button>
        </Space>

        {loading && <Alert type="info" showIcon message="正在检索当前上下文并生成回答" description="系统会尽量返回带引用的回答，证据不足时会明确提示。" />}
        {historyNotice && <Alert type="info" showIcon message="历史问答已恢复" description={historyNotice} closable onClose={() => setHistoryNotice(undefined)} />}

        {answer ? (
          <Card size="small" title="回答" className="knowledge-chat-answer">
            <Space wrap size={[8, 8]} style={{ marginBottom: 12 }}>
              <Tag color={answer.model_used ? 'green' : 'orange'}>{answer.model_used ? '模型已参与' : `模型未参与：${answer.model_error_code ?? answer.model_status}`}</Tag>
              <Tag color={answer.context_scope === 'current_file' ? 'purple' : 'blue'}>{answer.context_scope === 'current_file' ? '文件范围' : answer.context_scope === 'current_knowledge_base' ? '知识库范围' : '上下文范围'}</Tag>
              <Tag color={answer.insufficient_evidence ? 'red' : 'blue'}>{answer.insufficient_evidence ? '证据不足' : '引用支撑'}</Tag>
              <Tag>引用 {answer.citations.length} 条</Tag>
            </Space>
            {answer.insufficient_evidence && (
              <Alert
                type="warning"
                showIcon
                message="未找到充分依据，不能输出确定性结论"
                description="建议补充文件、缩小问题范围，或查看引用来源后再用于正式输出。若当前知识库为仅检索或禁止 AI，请先调整治理策略。"
                style={{ marginBottom: 12 }}
              />
            )}
            {(answer.model_error_code || answer.model_status === 'history' || answer.scenario) && (
              <Alert
                type="info"
                showIcon
                message="回答状态"
                description={`状态：${answer.model_status ?? 'generated'}${answer.model_error_code ? `；错误码：${answer.model_error_code}` : ''}${answer.scenario ? `；场景：${answer.scenario}` : ''}`}
                style={{ marginBottom: 12 }}
              />
            )}
            {structuredAnswer.length ? (
              <Space direction="vertical" size="small" style={{ width: '100%' }}>
                {structuredAnswer.map((section) => (
                  <Card key={section.title} size="small" type="inner" title={section.title} className="structured-answer-section">
                    <Typography.Paragraph style={{ whiteSpace: 'pre-wrap', marginBottom: 0 }}>{section.content}</Typography.Paragraph>
                  </Card>
                ))}
              </Space>
            ) : (
              <Typography.Paragraph style={{ whiteSpace: 'pre-wrap' }}>{answer.answer}</Typography.Paragraph>
            )}
            <Space wrap>
              <Button size="small" loading={feedbackLoading} onClick={() => submitFeedback('up')}>有帮助</Button>
              <Button size="small" danger loading={feedbackLoading} onClick={() => setFeedbackOpen(true)}>需改进</Button>
            </Space>
          </Card>
        ) : (
          <Empty description={knowledgeBaseId || currentFile ? '尚未发起问答' : '请选择知识库后开始问答'} />
        )}

        {answer && (
          <Card size="small" title="引用来源">
            <Space direction="vertical" style={{ width: '100%' }}>
              {answer.citations.length ? answer.citations.map((citation) => <CitationCard key={citation.chunk_id} citation={citation} onOpenFile={onOpenCitationFile} />) : <Empty description="本次回答没有可展示引用" />}
            </Space>
          </Card>
        )}

        <Card size="small" title="最近问答" extra={<Button size="small" loading={historyLoading} disabled={!knowledgeBaseId} onClick={() => loadHistory().catch((error) => message.warning(error.message || '问答历史加载失败'))}>刷新</Button>}>
          {history.length ? (
            <List
              size="small"
              dataSource={history.slice(0, 6)}
              renderItem={(item) => (
                <List.Item actions={[<Button size="small" onClick={() => restoreChat(item.id)}>恢复</Button>]}>
                  <List.Item.Meta title={item.title || '未命名问答'} description={new Date(item.created_at * 1000).toLocaleString()} />
                </List.Item>
              )}
            />
          ) : (
            <Empty description={knowledgeBaseId ? '当前知识库暂无问答历史' : '请选择知识库'} />
          )}
        </Card>
      </Space>

      <Modal
        title="反馈需改进原因"
        open={feedbackOpen}
        okText="提交反馈"
        cancelText="取消"
        confirmLoading={feedbackLoading}
        onCancel={() => setFeedbackOpen(false)}
        onOk={() => feedbackForm.submit()}
      >
        <Form form={feedbackForm} layout="vertical" onFinish={(values) => submitFeedback('down', values)} initialValues={{ issue_label: 'answer_inaccurate' }}>
          <Form.Item name="issue_label" label="问题类型" rules={[{ required: true, message: '请选择问题类型' }]}> 
            <Select options={feedbackIssueOptions} />
          </Form.Item>
          <Form.Item name="comment" label="补充说明">
            <Input.TextArea placeholder="可选：说明哪里不准确、缺少哪类引用或希望如何改进" autoSize={{ minRows: 3, maxRows: 6 }} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}
