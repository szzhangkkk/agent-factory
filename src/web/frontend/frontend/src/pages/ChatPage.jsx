import { useState, useRef, useEffect } from 'react'
import { Card, Input, Button, Space, Tag, Typography, Spin, Collapse } from 'antd'
import { SendOutlined, RobotOutlined, UserOutlined, LinkOutlined, ToolOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { chat, clearChatHistory } from '../api/client'

const { Text, Paragraph } = Typography

function ToolCallCard({ toolCall }) {
  const hasError = toolCall.error && toolCall.error.length > 0
  let argsDisplay = toolCall.arguments
  try {
    argsDisplay = JSON.stringify(JSON.parse(toolCall.arguments), null, 2)
  } catch { /* keep original */ }

  return (
    <div className={`tool-call-card${hasError ? ' has-error' : ''}`}>
      <Space size={8}>
        <ToolOutlined style={{ color: hasError ? 'var(--color-error)' : 'var(--accent)' }} />
        <Text strong style={{ fontSize: 12 }}>{toolCall.tool_name}</Text>
        {hasError && <Tag color="error" style={{ fontSize: 10 }}>错误</Tag>}
      </Space>
      <div style={{ marginTop: 4 }}>
        <Text type="secondary" style={{ fontSize: 11, fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
          {argsDisplay}
        </Text>
      </div>
      {(toolCall.result || toolCall.error) && (
        <div className="tool-call-result">
          <Text style={{ fontSize: 11, whiteSpace: 'pre-wrap', color: hasError ? 'var(--color-error)' : 'var(--text-secondary)' }}>
            {hasError ? toolCall.error : (toolCall.result.length > 300 ? toolCall.result.slice(0, 300) + '...' : toolCall.result)}
          </Text>
        </div>
      )}
    </div>
  )
}

function ReasoningSteps({ steps, iterations, toolCallsMade }) {
  if (!steps || steps.length === 0) return null

  return (
    <Collapse
      ghost
      size="small"
      items={[{
        key: 'steps',
        label: (
          <Space size={8}>
            <ThunderboltOutlined style={{ color: 'var(--color-gold)' }} />
            <Text style={{ fontSize: 12 }}>
              推理过程 ({iterations} 轮, {toolCallsMade} 次工具调用)
            </Text>
          </Space>
        ),
        children: (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {steps.map((step, i) => (
              <div key={i}>
                {step.content && (
                  <Text style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
                    {step.content}
                  </Text>
                )}
                {step.tool_calls && step.tool_calls.map((tc, j) => (
                  <ToolCallCard key={j} toolCall={tc} />
                ))}
              </div>
            ))}
          </div>
        ),
      }]}
      style={{ marginTop: 8 }}
    />
  )
}

export default function ChatPage() {
  const [agentDir, setAgentDir] = useState('./output')
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [showSources, setShowSources] = useState(true)
  const chatEnd = useRef(null)

  useEffect(() => {
    chatEnd.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    const q = input.trim()
    if (!q) return
    setMessages(prev => [...prev, { role: 'user', content: q }])
    setInput('')
    setLoading(true)
    try {
      const res = await chat({ agent_dir: agentDir, question: q, show_sources: showSources })
      const data = res.data
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.answer,
        sources: data.sources || [],
        strategy: data.retrieval_strategy,
        latency: data.retrieval_latency,
        chunks: data.chunks_used,
        reasoning_steps: data.reasoning_steps || [],
        iterations: data.iterations || 0,
        tool_calls_made: data.tool_calls_made || 0,
      }])
    } catch (e) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Error: ' + (e.response?.data?.detail || e.message),
        error: true,
      }])
    }
    setLoading(false)
  }

  return (
    <div className="chat-container">
      <Card size="small">
        <Space>
          <Text>Agent 目录:</Text>
          <Input value={agentDir} onChange={e => setAgentDir(e.target.value)} style={{ width: 300 }} placeholder="./output" />
          <Button size="small" onClick={() => { setMessages([]); clearChatHistory(agentDir) }}>清空对话</Button>
        </Space>
      </Card>

      <Card className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-empty">
            <RobotOutlined className="chat-empty-icon" />
            输入问题开始对话
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`chat-message${msg.role === 'user' ? ' user' : ''}`}>
            <div className={`chat-avatar${msg.role === 'user' ? ' user' : msg.error ? ' error' : ' assistant'}`}>
              {msg.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
            </div>
            <div className={`chat-bubble${msg.role === 'user' ? ' user' : ' assistant'}`}>
              <Paragraph style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{msg.content}</Paragraph>
              {msg.role === 'assistant' && msg.reasoning_steps && msg.reasoning_steps.length > 0 && (
                <ReasoningSteps
                  steps={msg.reasoning_steps}
                  iterations={msg.iterations}
                  toolCallsMade={msg.tool_calls_made}
                />
              )}
              {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 && (
                <div className="chat-source-divider">
                  <Space size={4} wrap>
                    <LinkOutlined style={{ color: 'var(--text-secondary)' }} />
                    {msg.sources.map((s, j) => <Tag key={j} color="default" style={{ fontSize: 11 }}>{s}</Tag>)}
                  </Space>
                  {msg.latency !== undefined && (
                    <div className="chat-meta">
                      Strategy: {msg.strategy} | Latency: {msg.latency?.toFixed(2)}s | Chunks: {msg.chunks}
                      {msg.tool_calls_made > 0 && ` | Tools: ${msg.tool_calls_made}`}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="chat-loading">
            <Spin />
          </div>
        )}
        <div ref={chatEnd} />
      </Card>

      <Card size="small">
        <Space.Compact style={{ width: '100%' }}>
          <Input
            value={input}
            onChange={e => setInput(e.target.value)}
            onPressEnter={handleSend}
            placeholder="输入问题..."
            size="large"
            disabled={loading}
          />
          <Button type="primary" icon={<SendOutlined />} size="large" loading={loading} onClick={handleSend}>
            发送
          </Button>
        </Space.Compact>
      </Card>
    </div>
  )
}
