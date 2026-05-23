import { useState, useRef, useEffect } from 'react'
import { Card, Input, Button, Space, Tag, Typography, Spin, Collapse } from 'antd'
import { SendOutlined, RobotOutlined, UserOutlined, LinkOutlined, ToolOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { chat } from '../api/client'

const { Text, Paragraph } = Typography

function ToolCallCard({ toolCall }) {
  const hasError = toolCall.error && toolCall.error.length > 0
  let argsDisplay = toolCall.arguments
  try {
    argsDisplay = JSON.stringify(JSON.parse(toolCall.arguments), null, 2)
  } catch { /* keep original */ }

  return (
    <div style={{
      background: '#1a1a2e', borderRadius: 8, padding: '8px 12px', marginBottom: 6,
      border: hasError ? '1px solid #ff4d4f' : '1px solid #333',
    }}>
      <Space size={8}>
        <ToolOutlined style={{ color: hasError ? '#ff4d4f' : '#1677ff' }} />
        <Text strong style={{ fontSize: 12 }}>{toolCall.tool_name}</Text>
        {hasError && <Tag color="error" style={{ fontSize: 10 }}>错误</Tag>}
      </Space>
      <div style={{ marginTop: 4 }}>
        <Text type="secondary" style={{ fontSize: 11, fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
          {argsDisplay}
        </Text>
      </div>
      {(toolCall.result || toolCall.error) && (
        <div style={{ marginTop: 4, padding: '4px 8px', background: '#111', borderRadius: 4, maxHeight: 120, overflow: 'auto' }}>
          <Text style={{ fontSize: 11, whiteSpace: 'pre-wrap', color: hasError ? '#ff7875' : '#aaa' }}>
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
            <ThunderboltOutlined style={{ color: '#faad14' }} />
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
                  <Text style={{ fontSize: 12, color: '#aaa', display: 'block', marginBottom: 4 }}>
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
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Card size="small">
        <Space>
          <Text>Agent 目录:</Text>
          <Input value={agentDir} onChange={e => setAgentDir(e.target.value)} style={{ width: 300 }} placeholder="./output" />
          <Button size="small" onClick={() => setMessages([])}>清空对话</Button>
        </Space>
      </Card>

      <Card style={{ minHeight: 400, maxHeight: '60vh', overflow: 'auto' }}>
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', color: '#666', padding: 60 }}>
            <RobotOutlined style={{ fontSize: 48, marginBottom: 16, display: 'block' }} />
            输入问题开始对话
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} style={{ marginBottom: 16, display: 'flex', gap: 12, flexDirection: msg.role === 'user' ? 'row-reverse' : 'row' }}>
            <div style={{
              width: 32, height: 32, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: msg.role === 'user' ? '#1677ff' : msg.error ? '#ff4d4f' : '#52c41a', flexShrink: 0,
            }}>
              {msg.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
            </div>
            <div style={{
              maxWidth: '75%', padding: '10px 14px', borderRadius: 12,
              background: msg.role === 'user' ? '#1677ff' : '#2a2a2a',
            }}>
              <Paragraph style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{msg.content}</Paragraph>
              {msg.role === 'assistant' && msg.reasoning_steps && msg.reasoning_steps.length > 0 && (
                <ReasoningSteps
                  steps={msg.reasoning_steps}
                  iterations={msg.iterations}
                  toolCallsMade={msg.tool_calls_made}
                />
              )}
              {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 && (
                <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid #333' }}>
                  <Space size={4} wrap>
                    <LinkOutlined style={{ color: '#999' }} />
                    {msg.sources.map((s, j) => <Tag key={j} color="default" style={{ fontSize: 11 }}>{s}</Tag>)}
                  </Space>
                  {msg.latency !== undefined && (
                    <Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 4 }}>
                      Strategy: {msg.strategy} | Latency: {msg.latency?.toFixed(2)}s | Chunks: {msg.chunks}
                      {msg.tool_calls_made > 0 && ` | Tools: ${msg.tool_calls_made}`}
                    </Text>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && <Spin style={{ marginLeft: 44 }} />}
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
    </Space>
  )
}
