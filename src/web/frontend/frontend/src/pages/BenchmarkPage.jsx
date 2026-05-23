import { useState } from 'react'
import { Card, Table, Tag, Space, Button, Progress, Descriptions, Empty } from 'antd'
import { BarChartOutlined, TrophyOutlined } from '@ant-design/icons'

const DEMO_DATA = [
  { key: '1', config: 'hybrid_rerank', recall: 0.92, precision: 0.85, mrr: 0.88, faithfulness: 0.91, relevance: 0.89, overall: 0.89, latency: 1.2 },
  { key: '2', config: 'hybrid', recall: 0.88, precision: 0.81, mrr: 0.84, faithfulness: 0.89, relevance: 0.86, overall: 0.86, latency: 0.9 },
  { key: '3', config: 'vector', recall: 0.78, precision: 0.72, mrr: 0.75, faithfulness: 0.82, relevance: 0.79, overall: 0.78, latency: 0.6 },
  { key: '4', config: 'bm25', recall: 0.71, precision: 0.65, mrr: 0.68, faithfulness: 0.78, relevance: 0.73, overall: 0.73, latency: 0.4 },
]

const colorScale = (val) => {
  if (val >= 0.9) return '#52c41a'
  if (val >= 0.8) return '#1677ff'
  if (val >= 0.7) return '#faad14'
  return '#ff4d4f'
}

const columns = [
  {
    title: '策略', dataIndex: 'config', key: 'config', fixed: 'left', width: 140,
    render: (text, _, idx) => (
      <Space>
        {idx === 0 && <TrophyOutlined style={{ color: '#faad14' }} />}
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
    render: v => <span style={{ color: v < 1 ? '#52c41a' : v < 2 ? '#faad14' : '#ff4d4f' }}>{v.toFixed(2)}s</span>,
  },
]

export default function BenchmarkPage() {
  const [data] = useState(DEMO_DATA)
  const best = data[0]

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
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
        <Tag color="blue">Agent 创建时自动生成</Tag>
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

      <Card size="small" style={{ textAlign: 'center', color: '#999' }}>
        Benchmark 数据在 Agent 创建时自动生成。创建新 Agent 后刷新此页面查看最新结果。
      </Card>
    </Space>
  )
}
