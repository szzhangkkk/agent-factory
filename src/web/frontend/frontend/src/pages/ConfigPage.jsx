import { useState } from 'react'
import { Card, Select, Input, Button, Form, Space, Tag, Alert, message, Collapse } from 'antd'
import { CheckCircleOutlined, CloseCircleOutlined, ApiOutlined, InfoCircleOutlined } from '@ant-design/icons'
import { updateConfig, testConnection } from '../api/client'

const LLM_PROVIDERS = [
  { id: 'deepseek', name: 'DeepSeek', url: 'https://api.deepseek.com/v1', models: ['deepchat', 'deepseek-reasoner'] },
  { id: 'qwen', name: '通义千问', url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', models: ['qwen-max', 'qwen-plus', 'qwen-turbo'] },
  { id: 'zhipu', name: '智谱 GLM', url: 'https://open.bigmodel.cn/api/paas/v4', models: ['glm-4-plus', 'glm-4-flash'] },
  { id: 'moonshot', name: 'Moonshot (Kimi)', url: 'https://api.moonshot.cn/v1', models: ['moonshot-v1-128k', 'moonshot-v1-32k'] },
  { id: 'claude', name: 'Claude', url: 'https://api.anthropic.com', models: ['claude-sonnet-4-6', 'claude-haiku-4-5-20251001'] },
  { id: 'openai', name: 'OpenAI', url: 'https://api.openai.com/v1', models: ['gpt-4o', 'gpt-4o-mini'] },
  { id: 'ollama', name: 'Ollama (本地)', url: 'http://localhost:11434/v1', models: ['qwen2.5:7b', 'llama3.1', 'deepseek-r1:7b'] },
  { id: 'custom', name: '自定义 (OpenAI 兼容)', url: '', models: [] },
]

const EMBEDDING_PRESETS = [
  { id: 'local', name: '本地模型 (无需 Key，推荐)', url: '', model: 'BAAI/bge-small-zh-v1.5', keyPlaceholder: '无需 Key，首次使用自动下载模型', docs: '' },
  { id: 'siliconflow', name: '硅基流动 (免费)', url: 'https://api.siliconflow.cn/v1', model: 'BAAI/bge-large-zh-v1.5', keyPlaceholder: '去 cloud.siliconflow.cn 免费注册获取', docs: 'https://cloud.siliconflow.cn/' },
  { id: 'openai', name: 'OpenAI Embedding', url: 'https://api.openai.com/v1', model: 'text-embedding-3-small', keyPlaceholder: 'sk-...', docs: 'https://platform.openai.com/' },
  { id: 'dashscope', name: '通义千问 Embedding', url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'text-embedding-v3', keyPlaceholder: '和通义千问 LLM 用同一个 key', docs: 'https://dashscope.console.aliyun.com/' },
  { id: 'ollama', name: 'Ollama 本地 Embedding', url: 'http://localhost:11434/v1', model: 'nomic-embed-text', keyPlaceholder: '本地无需 key', docs: '' },
  { id: 'custom', name: '自定义', url: '', model: '', keyPlaceholder: '' },
]

export default function ConfigPage() {
  // LLM state
  const [provider, setProvider] = useState('deepseek')
  const [baseUrl, setBaseUrl] = useState('https://api.deepseek.com/v1')
  const [apiKey, setApiKey] = useState('')
  const [model, setModel] = useState('deepseek-chat')
  // Embedding state
  const [embPreset, setEmbPreset] = useState('local')
  const [embUrl, setEmbUrl] = useState('')
  const [embKey, setEmbKey] = useState('')
  const [embModel, setEmbModel] = useState('BAAI/bge-small-zh-v1.5')
  // Test state
  const [testResult, setTestResult] = useState(null)
  const [testing, setTesting] = useState(false)

  const selectedLLM = LLM_PROVIDERS.find(p => p.id === provider)
  const selectedEmb = EMBEDDING_PRESETS.find(p => p.id === embPreset)

  const onLLMChange = (val) => {
    setProvider(val)
    const p = LLM_PROVIDERS.find(x => x.id === val)
    if (p) {
      setBaseUrl(p.url)
      if (p.models.length) setModel(p.models[0])
    }
  }

  const onEmbPresetChange = (val) => {
    setEmbPreset(val)
    const p = EMBEDDING_PRESETS.find(x => x.id === val)
    if (p) {
      setEmbUrl(p.url || '')
      setEmbModel(p.model || '')
      if (val === 'local' || val === 'ollama') setEmbKey('')
    }
  }

  const getEmbConfig = () => {
    const cfg = { provider: embPreset, base_url: embUrl, api_key: embKey, model: embModel }
    return cfg
  }

  const handleSave = async () => {
    try {
      await updateConfig({
        llm: { provider, base_url: baseUrl, api_key: apiKey, model },
        embedding: getEmbConfig(),
      })
      message.success('配置已保存')
    } catch (e) {
      message.error('保存失败: ' + (e.response?.data?.detail || e.message))
    }
  }

  const handleTest = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      await updateConfig({
        llm: { provider, base_url: baseUrl, api_key: apiKey, model },
        embedding: getEmbConfig(),
      })
      const res = await testConnection()
      setTestResult(res.data)
    } catch (e) {
      setTestResult({ error: e.response?.data?.detail || e.message })
    }
    setTesting(false)
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Alert
        type="info"
        showIcon
        icon={<InfoCircleOutlined />}
        message="LLM 和 Embedding 是两个独立服务"
        description="LLM 负责聊天/生成（如 DeepSeek），Embedding 负责将文本转为向量（如硅基流动）。两者需要分别配置，API Key 不通用。"
      />

      {/* LLM Configuration */}
      <Card title="LLM 模型配置（负责聊天/生成）" extra={<Tag color="blue">{selectedLLM?.name}</Tag>}>
        <Form layout="vertical" style={{ maxWidth: 600 }}>
          <Form.Item label="模型提供商">
            <Select value={provider} onChange={onLLMChange}>
              {LLM_PROVIDERS.map(p => <Select.Option key={p.id} value={p.id}>{p.name}</Select.Option>)}
            </Select>
          </Form.Item>
          <Form.Item label="API Base URL">
            <Input value={baseUrl} onChange={e => setBaseUrl(e.target.value)} />
          </Form.Item>
          <Form.Item label="API Key">
            <Input.Password value={apiKey} onChange={e => setApiKey(e.target.value)} placeholder="sk-..." />
          </Form.Item>
          <Form.Item label="模型名称">
            {selectedLLM?.models.length ? (
              <Select value={model} onChange={setModel}>
                {selectedLLM.models.map(m => <Select.Option key={m} value={m}>{m}</Select.Option>)}
              </Select>
            ) : (
              <Input value={model} onChange={e => setModel(e.target.value)} placeholder="model-name" />
            )}
          </Form.Item>
        </Form>
      </Card>

      {/* Embedding Configuration */}
      <Card title="Embedding 模型配置（负责文本向量化）" extra={<Tag color="green">{selectedEmb?.name}</Tag>}>
        <Form layout="vertical" style={{ maxWidth: 600 }}>
          <Form.Item label="Embedding 方案">
            <Select value={embPreset} onChange={onEmbPresetChange}>
              {EMBEDDING_PRESETS.map(p => <Select.Option key={p.id} value={p.id}>{p.name}</Select.Option>)}
            </Select>
            {selectedEmb?.docs && (
              <div style={{ marginTop: 4, fontSize: 12, color: 'var(--text-secondary)' }}>
                获取 Key: <a href={selectedEmb.docs} target="_blank" rel="noreferrer">{selectedEmb.docs}</a>
              </div>
            )}
          </Form.Item>
          <Form.Item label="Embedding API URL">
            <Input value={embUrl} onChange={e => setEmbUrl(e.target.value)} />
          </Form.Item>
          <Form.Item label="Embedding API Key">
            <Input.Password
              value={embKey}
              onChange={e => setEmbKey(e.target.value)}
              placeholder={selectedEmb?.keyPlaceholder || 'API Key'}
            />
          </Form.Item>
          <Form.Item label="Embedding 模型">
            <Input value={embModel} onChange={e => setEmbModel(e.target.value)} />
          </Form.Item>
        </Form>

        {embPreset === 'siliconflow' && (
          <Alert type="success" showIcon style={{ marginTop: 8 }}
            message="硅基流动免费额度足够开发测试"
            description="注册后在「API密钥」页面创建 Key，粘贴到上方即可。"
          />
        )}
      </Card>

      {/* Action Buttons */}
      <Space>
        <Button type="primary" icon={<ApiOutlined />} loading={testing} onClick={handleTest}>测试连接</Button>
        <Button onClick={handleSave}>保存配置</Button>
      </Space>

      {/* Test Results */}
      {testResult && (
        <Card size="small" title="连接测试结果">
          <Space direction="vertical" style={{ width: '100%' }}>
            {testResult.error && <Alert type="error" showIcon message={testResult.error} />}
            {testResult.llm && (
              <Space>
                <Tag>LLM</Tag>
                {testResult.llm.status === 'ok'
                  ? <Tag icon={<CheckCircleOutlined />} color="success">连接成功 — {testResult.llm.response}</Tag>
                  : <Tag icon={<CloseCircleOutlined />} color="error">{testResult.llm.error}</Tag>}
              </Space>
            )}
            {testResult.embedding && (
              <Space>
                <Tag>Embedding</Tag>
                {testResult.embedding.status === 'ok'
                  ? <Tag icon={<CheckCircleOutlined />} color="success">连接成功 — 维度 {testResult.embedding.dimension}</Tag>
                  : <Tag icon={<CloseCircleOutlined />} color="error">{testResult.embedding.error}</Tag>}
              </Space>
            )}
          </Space>
        </Card>
      )}

      {/* Help */}
      <Collapse size="small" items={[{
        key: '1',
        label: '常见问题',
        children: (
          <Space direction="vertical" size="small">
            <div><b>Q: DeepSeek 的 Key 能用于 Embedding 吗？</b><br/>A: 不能。DeepSeek 不提供 Embedding 服务，需要用硅基流动或其他 Embedding 服务。</div>
            <div><b>Q: 完全免费的方案？</b><br/>A: LLM 用 Ollama 本地模型，Embedding 用 Ollama 的 nomic-embed-text，全程零费用。</div>
            <div><b>Q: 测试连接报错怎么办？</b><br/>A: 分别测试 LLM 和 Embedding，哪个报错就检查哪个的 Key 和 URL。</div>
          </Space>
        ),
      }]} />
    </Space>
  )
}
