import { useState } from 'react'
import { Card, Form, Input, Button, Space, Steps, Tag, Descriptions, message, Spin, Switch } from 'antd'
import { RocketOutlined, CheckCircleOutlined, ToolOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { createAgent } from '../api/client'

export default function AgentPage() {
  const [docsPath, setDocsPath] = useState('./uploads')
  const [agentName, setAgentName] = useState('')
  const [agentDesc, setAgentDesc] = useState('')
  const [requirement, setRequirement] = useState('')
  const [skipBench, setSkipBench] = useState(false)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [step, setStep] = useState(0)

  const handleCreate = async () => {
    if (!docsPath) { message.warning('请填写文档路径'); return }
    setLoading(true)
    setStep(1)
    try {
      const res = await createAgent({
        docs_path: docsPath,
        agent_name: agentName || undefined,
        agent_description: agentDesc || undefined,
        user_requirement: requirement || undefined,
        skip_benchmark: skipBench,
      })
      setResult(res.data)
      setStep(2)
      message.success('Agent 创建成功!')
    } catch (e) {
      const detail = e.response?.data?.detail || e.message
      message.error({ content: '创建失败: ' + detail, duration: 10 })
      setStep(0)
    }
    setLoading(false)
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Steps
        current={step}
        items={[
          { title: '配置', description: '填写需求' },
          { title: '生成中', description: loading ? '处理中...' : '等待开始' },
          { title: '完成', description: result ? '已生成' : '' },
        ]}
      />

      <Card title="Agent 配置">
        <Form layout="vertical" style={{ maxWidth: 640 }}>
          <Form.Item label="文档路径" required>
            <Input value={docsPath} onChange={e => setDocsPath(e.target.value)} placeholder="./uploads 或 ./docs/manual.pdf" />
          </Form.Item>
          <Form.Item label="Agent 名称">
            <Input value={agentName} onChange={e => setAgentName(e.target.value)} placeholder="如：产品客服助手" />
          </Form.Item>
          <Form.Item label="Agent 描述">
            <Input.TextArea value={agentDesc} onChange={e => setAgentDesc(e.target.value)} rows={2} placeholder="简要描述 Agent 的用途" />
          </Form.Item>
          <Form.Item label="具体需求（可选）">
            <Input.TextArea value={requirement} onChange={e => setRequirement(e.target.value)} rows={3} placeholder="如：用户问退款问题时，需要查询文档中退款相关章节并准确回答" />
          </Form.Item>
          <Form.Item label="跳过 Benchmark">
            <Switch checked={skipBench} onChange={setSkipBench} />
            <span style={{ marginLeft: 8, color: '#999' }}>{skipBench ? '跳过评测，更快生成' : '自动评测选择最优配置'}</span>
          </Form.Item>
          <Form.Item>
            <Button type="primary" icon={<RocketOutlined />} size="large" loading={loading} onClick={handleCreate}>
              生成 Agent
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {result && (
        <Card title="生成结果" extra={<Tag icon={<CheckCircleOutlined />} color="success">已完成</Tag>}>
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="Agent 名称">{result.agent_name}</Descriptions.Item>
            <Descriptions.Item label="输出目录">{result.output_dir}</Descriptions.Item>
            <Descriptions.Item label="最优检索策略">{result.best_config}</Descriptions.Item>
            <Descriptions.Item label="推理策略">
              <Tag icon={<ThunderboltOutlined />} color="processing">
                {result.reasoning_strategy || 'direct'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="可用工具">
              <Space size={4} wrap>
                {(result.tools || []).map((t, i) => (
                  <Tag key={i} icon={<ToolOutlined />} color="blue">{t.type}</Tag>
                ))}
                {(!result.tools || result.tools.length === 0) && <Tag color="default">无额外工具</Tag>}
              </Space>
            </Descriptions.Item>
            {result.benchmark_scores && (
              <>
                <Descriptions.Item label="综合评分">{result.benchmark_scores.overall_score}</Descriptions.Item>
                <Descriptions.Item label="Recall">{result.benchmark_scores.recall}</Descriptions.Item>
                <Descriptions.Item label="Faithfulness">{result.benchmark_scores.faithfulness}</Descriptions.Item>
                <Descriptions.Item label="Relevance">{result.benchmark_scores.relevance}</Descriptions.Item>
              </>
            )}
          </Descriptions>
          <div style={{ marginTop: 16, color: '#999' }}>
            前往 "对话测试" 页面与 Agent 对话，可以观察到 Agent 使用工具和推理的过程。
          </div>
        </Card>
      )}
    </Space>
  )
}
