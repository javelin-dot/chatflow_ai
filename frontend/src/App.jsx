import React from 'react'
import { Routes, Route, Link } from 'react-router-dom'
import { Layout, Menu } from 'antd'
import {
  CloudServerOutlined,
  BuildOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons'

import ServiceManager from './pages/ServiceManager.jsx'
function WorkflowBuilder() {
  return <div>Workflow Builder (coming soon)</div>
}
function WorkflowRunner() {
  return <div>Workflow Runner (coming soon)</div>
}

const { Header, Content } = Layout

function App() {
  const menuItems = [
    {
      key: 'services',
      icon: <CloudServerOutlined />,
      label: <Link to="/">服务管理</Link>,
    },
    {
      key: 'builder',
      icon: <BuildOutlined />,
      label: <Link to="/builder">流程编排</Link>,
    },
    {
      key: 'runner',
      icon: <PlayCircleOutlined />,
      label: <Link to="/runner">流程执行</Link>,
    },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center' }}>
        <div style={{ color: 'white', fontSize: 18, fontWeight: 'bold', marginRight: 24 }}>
          ChatFlow Workflow
        </div>
        <Menu
          theme="dark"
          mode="horizontal"
          items={menuItems}
          style={{ flex: 1 }}
        />
      </Header>
      <Content style={{ padding: 24 }}>
        <Routes>
          <Route path="/" element={<ServiceManager />} />
          <Route path="/builder" element={<WorkflowBuilder />} />
          <Route path="/runner" element={<WorkflowRunner />} />
        </Routes>
      </Content>
    </Layout>
  )
}

export default App
