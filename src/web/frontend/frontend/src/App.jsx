import { useState } from 'react'
import { ConfigProvider, Layout, Menu } from 'antd'
import { RobotOutlined, SettingOutlined, FileTextOutlined, BarChartOutlined, MessageOutlined, AppstoreOutlined } from '@ant-design/icons'
import ConfigPage from './pages/ConfigPage'
import DocumentsPage from './pages/DocumentsPage'
import AgentPage from './pages/AgentPage'
import ChatPage from './pages/ChatPage'
import BenchmarkPage from './pages/BenchmarkPage'
import AgentManagePage from './pages/AgentManagePage'
import './App.css'

const { Header, Sider, Content } = Layout

const PAGES = {
  config: { label: '模型配置', icon: <SettingOutlined />, component: ConfigPage },
  documents: { label: '文档管理', icon: <FileTextOutlined />, component: DocumentsPage },
  agent: { label: 'Agent 创建', icon: <RobotOutlined />, component: AgentPage },
  benchmark: { label: 'Benchmark', icon: <BarChartOutlined />, component: BenchmarkPage },
  chat: { label: '对话测试', icon: <MessageOutlined />, component: ChatPage },
  agents: { label: 'Agent 管理', icon: <AppstoreOutlined />, component: AgentManagePage },
}

function App() {
  const [currentPage, setCurrentPage] = useState('config')
  const PageComponent = PAGES[currentPage].component

  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#6e56cf',
          colorBgBase: '#f4f4f5',
          colorBgContainer: '#ffffff',
          colorBgElevated: '#ffffff',
          colorBorderSecondary: '#e5e5e5',
          colorText: '#18181b',
          colorTextSecondary: '#71717a',
          colorTextTertiary: '#a1a1aa',
          borderRadius: 8,
          fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', Roboto, sans-serif",
          colorLink: '#6e56cf',
          colorSuccess: '#16a34a',
          colorWarning: '#d97706',
          colorError: '#dc2626',
          colorInfo: '#6e56cf',
          controlHeight: 34,
        },
        components: {
          Menu: {
            itemBg: 'transparent',
            subMenuItemBg: 'transparent',
            itemSelectedBg: 'rgba(110, 86, 207, 0.07)',
            itemHoverBg: 'rgba(0, 0, 0, 0.03)',
            itemSelectedColor: '#6e56cf',
            itemBorderRadius: 5,
            iconSize: 14,
          },
          Card: {
            colorBgContainer: '#ffffff',
            colorBorderSecondary: '#e5e5e5',
          },
          Button: {
            primaryShadow: 'none',
          },
          Table: {
            colorBgContainer: 'transparent',
            headerBg: '#f9f9f9',
            headerColor: '#71717a',
            rowHoverBg: 'rgba(110, 86, 207, 0.025)',
            borderColor: '#e5e5e5',
          },
          Input: {
            colorBgContainer: '#ffffff',
            activeBorderColor: '#6e56cf',
            hoverBorderColor: '#d4d4d8',
          },
          Select: {
            colorBgContainer: '#ffffff',
            optionSelectedBg: 'rgba(110, 86, 207, 0.07)',
          },
          Tag: {
            borderRadiusSM: 5,
          },
          Steps: {
            colorPrimary: '#6e56cf',
          },
          Progress: {
            colorBgBase: '#f4f4f5',
          },
          Collapse: {
            colorBgContainer: '#ffffff',
            headerBg: '#ffffff',
            contentBg: '#ffffff',
          },
          Alert: {
            colorInfoBg: 'rgba(110, 86, 207, 0.05)',
            colorInfoBorder: 'rgba(110, 86, 207, 0.12)',
          },
        },
      }}
    >
      <Layout className="app-layout">
        {/* Activity Bar */}
        <div className="app-activity-bar">
          {Object.entries(PAGES).map(([key, val]) => (
            <div
              key={key}
              className={`app-activity-item${currentPage === key ? ' active' : ''}`}
              onClick={() => setCurrentPage(key)}
              title={val.label}
            >
              {val.icon}
            </div>
          ))}
        </div>

        {/* Sidebar */}
        <Sider width={180} className="app-sider">
          <div className="app-logo">
            <div className="app-logo-icon">
              <RobotOutlined style={{ color: '#fff', fontSize: 14 }} />
            </div>
            <span className="app-logo-text">Agent Factory</span>
          </div>
          <Menu
            mode="inline"
            selectedKeys={[currentPage]}
            items={Object.entries(PAGES).map(([key, val]) => ({
              key,
              label: val.label,
            }))}
            onClick={({ key }) => setCurrentPage(key)}
            style={{ background: 'transparent', border: 'none', marginTop: 4 }}
          />
          <div className="app-sider-footer">v1.0.0</div>
        </Sider>

        {/* Main */}
        <Layout>
          <Header className="app-header">
            <h2>{PAGES[currentPage].label}</h2>
          </Header>
          <Content className="app-content">
            <PageComponent />
          </Content>
        </Layout>
      </Layout>
    </ConfigProvider>
  )
}

export default App
