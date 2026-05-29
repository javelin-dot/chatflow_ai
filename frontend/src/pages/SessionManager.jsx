import React, { useState, useEffect } from 'react'
import {
  Card,
  Input,
  Button,
  Select,
  Table,
  message,
  Space,
  Popconfirm,
} from 'antd'
import { LoginOutlined, DeleteOutlined } from '@ant-design/icons'
import { servicesApi, sessionsApi } from '../api/client.js'

function SessionManager() {
  const [services, setServices] = useState([])
  const [loginService, setLoginService] = useState('')
  const [operations, setOperations] = useState([])
  const [loginOperation, setLoginOperation] = useState('')
  const [credentials, setCredentials] = useState('{}')
  const [targetService, setTargetService] = useState('')
  const [tokenPath, setTokenPath] = useState('data.token')
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(false)
  const [loginLoading, setLoginLoading] = useState(false)

  const fetchServices = async () => {
    try {
      const res = await servicesApi.list()
      setServices(res.data || [])
    } catch (err) {
      message.error('获取服务列表失败')
    }
  }

  const fetchSessions = async () => {
    try {
      const res = await sessionsApi.get()
      setSessions(res.data || [])
    } catch (err) {
      message.error('获取会话列表失败')
    }
  }

  useEffect(() => {
    fetchServices()
    fetchSessions()
  }, [])

  useEffect(() => {
    if (!loginService) {
      setOperations([])
      return
    }
    const fetchOps = async () => {
      setLoading(true)
      try {
        const res = await servicesApi.getOperations(loginService)
        setOperations(res.data || [])
      } catch (err) {
        message.error('获取接口列表失败')
      } finally {
        setLoading(false)
      }
    }
    fetchOps()
  }, [loginService])

  const handleLogin = async () => {
    if (!loginService || !loginOperation) {
      message.warning('请选择登录服务和接口')
      return
    }
    let parsedCredentials
    try {
      parsedCredentials = JSON.parse(credentials)
    } catch {
      message.error('请求体 JSON 格式错误')
      return
    }
    setLoginLoading(true)
    try {
      const payload = {
        service_id: loginService,
        operation_id: loginOperation,
        credentials: parsedCredentials,
        token_path: tokenPath || undefined,
        target_service: targetService || undefined,
      }
      await sessionsApi.login(payload)
      message.success('登录成功')
      setCredentials('{}')
      setLoginOperation('')
      fetchSessions()
    } catch (err) {
      const msg = err?.response?.data?.detail || err.message || '未知错误'
      message.error(`登录失败: ${msg}`)
    } finally {
      setLoginLoading(false)
    }
  }

  const handleClear = async (serviceId) => {
    try {
      await sessionsApi.clear(serviceId)
      message.success('清除成功')
      fetchSessions()
    } catch (err) {
      message.error('清除失败')
    }
  }

  const serviceOptions = services.map((s) => ({
    value: s.name,
    label: s.name,
  }))

  const operationOptions = operations.map((op) => ({
    value: op.operation_id,
    label: `${op.method} ${op.path} — ${op.operation_id}`,
  }))

  const columns = [
    { title: '服务名称', dataIndex: 'service_id', key: 'service_id' },
    { title: '登录接口', dataIndex: 'operation_id', key: 'operation_id' },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Popconfirm
          title="确认清除"
          description={`确定要清除服务 "${record.service_id}" 的会话吗？`}
          onConfirm={() => handleClear(record.service_id)}
          okText="清除"
          cancelText="取消"
        >
          <Button icon={<DeleteOutlined />} size="small" danger>
            清除
          </Button>
        </Popconfirm>
      ),
    },
  ]

  return (
    <Space direction="vertical" style={{ display: 'flex' }} size="large">
      <Card title="登录认证">
        <Space direction="vertical" style={{ display: 'flex' }}>
          <Select
            placeholder="选择登录服务"
            showSearch
            filterOption={(input, option) =>
              (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
            }
            value={loginService || undefined}
            onChange={setLoginService}
            options={serviceOptions}
            style={{ width: '100%' }}
          />
          <Select
            placeholder="选择登录接口"
            showSearch
            filterOption={(input, option) =>
              (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
            }
            value={loginOperation || undefined}
            onChange={setLoginOperation}
            options={operationOptions}
            loading={loading}
            style={{ width: '100%' }}
          />
          <Input.TextArea
            placeholder='请求体 JSON，如 {"username":"admin","password":"123456"}'
            value={credentials}
            onChange={(e) => setCredentials(e.target.value)}
            rows={3}
          />
          <Select
            placeholder="目标服务（可选，跨服务登录时填写）"
            showSearch
            filterOption={(input, option) =>
              (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
            }
            value={targetService || undefined}
            onChange={setTargetService}
            options={serviceOptions}
            style={{ width: '100%' }}
            allowClear
          />
          <Input
            placeholder="Token 提取路径（可选，默认 data.token）"
            value={tokenPath}
            onChange={(e) => setTokenPath(e.target.value)}
          />
          <Button
            type="primary"
            icon={<LoginOutlined />}
            onClick={handleLogin}
            loading={loginLoading}
          >
            登录
          </Button>
        </Space>
      </Card>

      <Card title="已登录会话">
        <Table
          rowKey="service_id"
          columns={columns}
          dataSource={sessions}
          pagination={false}
        />
      </Card>
    </Space>
  )
}

export default SessionManager
