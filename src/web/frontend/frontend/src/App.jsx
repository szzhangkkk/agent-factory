import { useState } from 'react'
import { ConfigProvider, Layout, Menu, theme } from 'antd'
import { RobotOutlined, SettingOutlined, FileTextOutlined, BarChartOutlined, MessageOutlined } from '@ant-design/icons'
import ConfigPage from './pages/ConfigPage'
import DocumentsPage from './pages/DocumentsPage'
import AgentPage from './pages/AgentPage'
import ChatPage from './pages/ChatPage'
import BenchmarkPage from './pages/BenchmarkPage'
import './App.css'

const { Header, Sider, Content } = Layout

const PAGES = {
  config: { label: '模型配置', icon: <SettingOutlined />, component: ConfigPage },
  documents: { label: '文档管理', icon: <FileTextOutlined />, component: DocumentsPage },
  agent: { label: 'Agent 创建', icon: <RobotOutlined />, component: AgentPage },
  benchmark: { label: 'Benchmark', icon: <BarChartOutlined />, component: BenchmarkPage },
  chat: { label: '对话测试', icon: <MessageOutlined />, component: ChatPage },
}

function App() {
  const [currentPage, setCurrentPage] = useState('config')
  const PageComponent = PAGES[currentPage].component

  return (
    <ConfigProvider
      theme={{
        algorithm: theme.darkAlgorithm,
        token: { colorPrimary: '#1677ff', borderRadius: 8 },
      }}
    >
      <Layout style={{ minHeight: '100vh' }}>
        <Sider width={200} theme="dark">
          <div style={{ padding: '16px 24px', color: '#fff', fontSize: 18, fontWeight: 700 }}>
            AgentOS
          </div>
          <Menu
            theme="dark"
            mode="inline"
            selectedKeys={[currentPage]}
            items={Object.entries(PAGES).map(([key, val]) => ({
              key,
              icon: val.icon,
              label: val.label,
            }))}
            onClick={({ key }) => setCurrentPage(key)}
          />
        </Sider>
        <Layout>
          <Header style={{ background: '#141414', padding: '0 24px', display: 'flex', alignItems: 'center' }}>
            <h2 style={{ color: '#fff', margin: 0 }}>{PAGES[currentPage].label}</h2>
          </Header>
          <Content style={{ margin: 16, padding: 24, background: '#1a1a1a', borderRadius: 8, overflow: 'auto' }}>
            <PageComponent />
          </Content>
        </Layout>
      </Layout>
    </ConfigProvider>
  )
}

export default App
