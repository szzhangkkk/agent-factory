import { useState, useEffect } from 'react'
import { Card, List, Tag, Space, Button, Empty, Popconfirm, message, Descriptions, Input, Modal, Form } from 'antd'
import { RobotOutlined, DeleteOutlined, ReloadOutlined, ThunderboltOutlined, ToolOutlined, CheckCircleOutlined, DownloadOutlined, PlusOutlined, ApiOutlined } from '@ant-design/icons'
import api from '../api/client'

export default function AgentManagePage() {
  const [agents, setAgents] = useState([])
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState(null)
  const [customTools, setCustomTools] = useState([])
  const [showToolModal, setShowToolModal] = useState(false)
  const [toolForm] = Form.useForm()

  const fetchAgents = async () => {
    setLoading(true)
    try {
      const res = await api.get('/agents/list')
      setAgents(res.data.agents || [])
    } catch (e) {
      message.error('加载失败: ' + (e.response?.data?.detail || e.message))
    }
    setLoading(false)
  }

  const handleDelete = async (name) => {
    try {
      await api.delete(`/agents/${name}`)
      message.success(`已删除 ${name}`)
      if (selected?.name === name) setSelected(null)
      fetchAgents()
    } catch (e) {
      message.error('删除失败: ' + (e.response?.data?.detail || e.message))
    }
  }

  const handleExport = (name) => {
    window.open(`/agents/${name}/export`, '_blank')
  }

  const fetchTools = async (agentName) => {
    try {
      const res = await api.get(`/agents/${agentName}/tools`)
      setCustomTools(res.data.tools || [])
    } catch { setCustomTools([]) }
  }

  const handleAddTool = async () => {
    try {
      const values = await toolForm.validateFields()
      await api.post(`/agents/${selected.name}/tools`, {
        name: values.tool_name,
        description: values.tool_desc || '',
        url: values.tool_url,
        method: values.tool_method || 'POST',
        parameters: { type: 'object', properties: { query: { type: 'string', description: '输入参数' } }, required: ['query'] },
      })
      message.success('工具已添加')
      setShowToolModal(false)
      toolForm.resetFields()
      fetchTools(selected.name)
    } catch (e) {
      if (e.response) message.error('添加失败: ' + (e.response?.data?.detail || e.message))
    }
  }

  const handleDeleteTool = async (toolName) => {
    try {
      await api.delete(`/agents/${selected.name}/tools/${toolName}`)
      message.success('工具已删除')
      fetchTools(selected.name)
    } catch (e) {
      message.error('删除失败')
    }
  }

  useEffect(() => { fetchAgents() }, [])

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Card size="small">
        <Space>
          <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>
            共 {agents.length} 个 Agent
          </span>
          <Button icon={<ReloadOutlined />} size="small" onClick={fetchAgents} loading={loading}>刷新</Button>
        </Space>
      </Card>

      {agents.length === 0 && !loading && (
        <Card>
          <Empty
            image={<RobotOutlined style={{ fontSize: 48, color: 'var(--text-tertiary)' }} />}
            description="还没有创建任何 Agent"
          >
            <span style={{ color: 'var(--text-tertiary)', fontSize: 13 }}>
              前往「Agent 创建」页面生成你的第一个 Agent
            </span>
          </Empty>
        </Card>
      )}

      {agents.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 12 }}>
          {agents.map((agent) => (
            <Card
              key={agent.name}
              size="small"
              hoverable
              onClick={() => { const s = selected?.name === agent.name ? null : agent; setSelected(s); if (s) fetchTools(s.name); else setCustomTools([]) }}
              style={{ cursor: 'pointer' }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>
                    {agent.agent_name || agent.name}
                  </div>
                  {agent.description && (
                    <div style={{ color: 'var(--text-secondary)', fontSize: 12, marginBottom: 8, lineHeight: 1.5 }}>
                      {agent.description}
                    </div>
                  )}
                  <Space size={4} wrap>
                    <Tag color="processing" icon={<ThunderboltOutlined />} style={{ fontSize: 11 }}>
                      {agent.reasoning_strategy}
                    </Tag>
                    <Tag color="default" icon={<ToolOutlined />} style={{ fontSize: 11 }}>
                      {agent.strategy}
                    </Tag>
                    {agent.has_benchmark && <Tag color="success" style={{ fontSize: 11 }}>Benchmark</Tag>}
                    {agent.has_history && <Tag color="warning" style={{ fontSize: 11 }}>有对话记录</Tag>}
                  </Space>
                </div>
                <Space size={0}>
                  <Button
                    type="text"
                    icon={<DownloadOutlined />}
                    size="small"
                    title="导出部署包"
                    onClick={(e) => { e.stopPropagation(); handleExport(agent.name) }}
                  />
                  <Popconfirm
                    title="确定删除此 Agent？"
                    description="删除后不可恢复"
                    onConfirm={(e) => { e.stopPropagation(); handleDelete(agent.name) }}
                    onCancel={(e) => e.stopPropagation()}
                  >
                    <Button
                      type="text"
                      danger
                      icon={<DeleteOutlined />}
                      size="small"
                      onClick={(e) => e.stopPropagation()}
                    />
                  </Popconfirm>
                </Space>
              </div>
            </Card>
          ))}
        </div>
      )}

      {selected && (
        <Card title="Agent 详情" extra={<Tag icon={<CheckCircleOutlined />} color="success">已选择</Tag>}>
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="目录名">{selected.name}</Descriptions.Item>
            <Descriptions.Item label="路径">{selected.path}</Descriptions.Item>
            <Descriptions.Item label="推理策略">
              <Tag color="processing">{selected.reasoning_strategy}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="检索策略">{selected.strategy}</Descriptions.Item>
            <Descriptions.Item label="Benchmark">{selected.has_benchmark ? '已完成' : '未生成'}</Descriptions.Item>
            <Descriptions.Item label="对话记录">{selected.has_history ? '有历史记录' : '无'}</Descriptions.Item>
          </Descriptions>
          <div style={{ marginTop: 12, display: 'flex', gap: 8, alignItems: 'center' }}>
            <Button icon={<DownloadOutlined />} size="small" onClick={() => handleExport(selected.name)}>
              导出部署包
            </Button>
            <span style={{ color: 'var(--text-tertiary)', fontSize: 12 }}>
              前往「对话测试」，Agent 目录填: {selected.path}
            </span>
          </div>
        </Card>
      )}

      {selected && (
        <Card
          title={<><ApiOutlined /> 自定义工具</>}
          extra={<Button icon={<PlusOutlined />} size="small" onClick={() => setShowToolModal(true)}>添加工具</Button>}
        >
          {customTools.length === 0 ? (
            <div style={{ color: 'var(--text-tertiary)', fontSize: 13, padding: '8px 0' }}>
              暂无自定义工具。添加 HTTP API 工具让 Agent 可以调用外部服务。
            </div>
          ) : (
            <List
              size="small"
              dataSource={customTools}
              renderItem={(tool) => (
                <List.Item
                  actions={[
                    <Popconfirm title="确定删除？" onConfirm={() => handleDeleteTool(tool.name)}>
                      <Button type="text" danger icon={<DeleteOutlined />} size="small" />
                    </Popconfirm>
                  ]}
                >
                  <List.Item.Meta
                    avatar={<ApiOutlined style={{ color: 'var(--accent)', fontSize: 16 }} />}
                    title={<span style={{ fontSize: 13 }}>{tool.name} <Tag style={{ fontSize: 10 }}>{tool.method}</Tag></span>}
                    description={<span style={{ fontSize: 11 }}>{tool.description} — {tool.url}</span>}
                  />
                </List.Item>
              )}
            />
          )}
        </Card>
      )}

      <Modal
        title="添加自定义工具"
        open={showToolModal}
        onOk={handleAddTool}
        onCancel={() => { setShowToolModal(false); toolForm.resetFields() }}
        okText="添加"
        cancelText="取消"
      >
        <Form form={toolForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="tool_name" label="工具名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="如: search_products" />
          </Form.Item>
          <Form.Item name="tool_desc" label="描述">
            <Input placeholder="工具功能描述" />
          </Form.Item>
          <Form.Item name="tool_url" label="API URL" rules={[{ required: true, message: '请输入 URL' }]}>
            <Input placeholder="https://api.example.com/search" />
          </Form.Item>
          <Form.Item name="tool_method" label="HTTP 方法" initialValue="POST">
            <Input placeholder="POST" />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  )
}
