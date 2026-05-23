import { useState, useEffect } from 'react'
import { Card, Table, Tag, Space, Progress, Descriptions, Input, Button, Spin, message } from 'antd'
import { BarChartOutlined, TrophyOutlined, ReloadOutlined } from '@ant-design/icons'
import { getBenchmark } from '../api/client'

const colorScale = (val) => {
  if (val >= 0.9) return '#22c55e'
  if (val >= 0.8) return '#6e56cf'
  if (val >= 0.7) return '#eab308'
  return '#ef4444'
}

const columns = [
  {
    title: '策略', dataIndex: 'config', key: 'config', fixed: 'left', width: 140,
    render: (text, _, idx) => (
      <Space>
        {idx === 0 && <TrophyOutlined style={{ color: '#eab308' }} />}
        <Tag color={idx === 0 ? 'gold' : 'default'}>{text}</Tag>
      </Space>
    ),
  },
  {
    title: 'Recall', dataIndex: 'recall', key: 'recall', sorter: (a, b) => a.recall - b.recall,
    render: v => <Progress percent={Math.round(v * 100)} size="small" strokeColor={colorScale(v)} format={p => `${p}%`} />,
  },
  {
    title: 'Precision', dataIndex: 'precision', key: 'precision', sorter: (a, b) => a.precision - b.precision,
    render: v => <Progress percent={Math.round(v * 100)} size="small" strokeColor={colorScale(v)} format={p => `${p}%`} />,
  },
  {
    title: 'MRR', dataIndex: 'mrr', key: 'mrr', sorter: (a, b) => a.mrr - b.mrr,
    render: v => <Progress percent={Math.round(v * 100)} size="small" strokeColor={colorScale(v)} format={p => `${p}%`} />,
  },
  {
    title: 'Faithfulness', dataIndex: 'faithfulness', key: 'faithfulness', sorter: (a, b) => a.faithfulness - b.faithfulness,
    render: v => <Progress percent={Math.round(v * 100)} size="small" strokeColor={colorScale(v)} format={p => `${p}%`} />,
  },
  {
    title: 'Relevance', dataIndex: 'relevance', key: 'relevance', sorter: (a, b) => a.relevance - b.relevance,
    render: v => <Progress percent={Math.round(v * 100)} size="small" strokeColor={colorScale(v)} format={p => `${p}%`} />,
  },
  {
    title: 'Overall', dataIndex: 'overall', key: 'overall', sorter: (a, b) => a.overall - b.overall, defaultSortOrder: 'descend',
    render: v => <Tag color={colorScale(v)} style={{ fontWeight: 700 }}>{(v * 100).toFixed(1)}%</Tag>,
  },
  {
    title: 'Latency (s)', dataIndex: 'latency', key: 'latency', sorter: (a, b) => a.latency - b.latency,
    render: v => <span style={{ color: v < 1 ? '#22c55e' : v < 2 ? '#eab308' : '#ef4444' }}>{v.toFixed(2)}s</span>,
  },
]

export default function BenchmarkPage() {
  const [agentDir, setAgentDir] = useState('./output')
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(false)
  const [message_, setMessage] = useState('')

  const fetchBenchmark = async () => {
    setLoading(true)
    try {
      const res = await getBenchmark(agentDir)
      const result = res.data
      if (result.data && result.data.length > 0) {
        setData(result.data.map((item, i) => ({ ...item, key: String(i) })))
        setMessage('')
      } else {
        setData([])
        setMessage(result.message || '暂无 Benchmark 数据')
      }
    } catch (e) {
      message.error('获取数据失败: ' + (e.response?.data?.detail || e.message))
      setData([])
    }
    setLoading(false)
  }

  useEffect(() => {
    fetchBenchmark()
  }, [])

  const best = data.length > 0 ? data[0] : null

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card size="small">
        <Space>
          <span style={{ color: 'var(--text-secondary)' }}>Agent 目录:</span>
          <Input value={agentDir} onChange={e => setAgentDir(e.target.value)} style={{ width: 300 }} placeholder="./output" />
          <Button icon={<ReloadOutlined />} loading={loading} onClick={fetchBenchmark}>刷新数据</Button>
        </Space>
      </Card>

      {loading && (
        <Card style={{ textAlign: 'center', padding: 40 }}>
          <Spin size="large" />
          <div style={{ marginTop: 16, color: 'var(--text-secondary)' }}>正在加载 Benchmark 数据...</div>
        </Card>
      )}

      {!loading && data.length === 0 && (
        <Card style={{ textAlign: 'center', padding: 40, color: 'var(--text-tertiary)' }}>
          <BarChartOutlined style={{ fontSize: 40, marginBottom: 12, display: 'block', color: 'var(--text-tertiary)' }} />
          <div style={{ fontSize: 16, marginBottom: 8 }}>{message_ || '暂无 Benchmark 数据'}</div>
          <div style={{ fontSize: 13 }}>请先创建 Agent（不要勾选"跳过 Benchmark"），完成后刷新此页面</div>
        </Card>
      )}

      {!loading && best && (
        <>
          <Card>
            <Descriptions bordered column={3} size="small">
              <Descriptions.Item label={<><TrophyOutlined /> 最优策略</>}>
                <Tag color="gold" style={{ fontSize: 14 }}>{best.config}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="综合评分">
                <span style={{ fontSize: 20, fontWeight: 700, color: colorScale(best.overall) }}>
                  {(best.overall * 100).toFixed(1)}%
                </span>
              </Descriptions.Item>
              <Descriptions.Item label="平均延迟">
                <span style={{ fontSize: 16 }}>{best.latency}s</span>
              </Descriptions.Item>
            </Descriptions>
          </Card>

          <Card title={<><BarChartOutlined /> Benchmark 对比结果</>} extra={
            <Tag color="blue">共 {data.length} 种策略</Tag>
          }>
            <Table
              columns={columns}
              dataSource={data}
              pagination={false}
              size="middle"
              scroll={{ x: 900 }}
              rowClassName={(_, idx) => idx === 0 ? 'ant-table-row-selected' : ''}
            />
          </Card>

          <Card title="指标说明" size="small">
            <Descriptions column={2} size="small" bordered>
              <Descriptions.Item label="Recall">检索结果中包含了多少正确答案的原文段落</Descriptions.Item>
              <Descriptions.Item label="Precision">检索结果中有多少是真正相关的</Descriptions.Item>
              <Descriptions.Item label="MRR">第一个正确结果排在第几位 (越高越好)</Descriptions.Item>
              <Descriptions.Item label="Faithfulness">生成的回答是否忠于检索到的文档 (不幻觉)</Descriptions.Item>
              <Descriptions.Item label="Relevance">回答是否真正回答了用户的问题</Descriptions.Item>
              <Descriptions.Item label="Overall">综合加权评分</Descriptions.Item>
            </Descriptions>
          </Card>
        </>
      )}
    </Space>
  )
}
