import React, { useState, useEffect } from 'react'
import { Card, Input, Button, Table, message, Space } from 'antd'
import { servicesApi } from '../api/client.js'

function ServiceManager() {
  const [name, setName] = useState('')
  const [url, setUrl] = useState('')
  const [services, setServices] = useState([])
  const [loading, setLoading] = useState(false)

  const fetchServices = async () => {
    setLoading(true)
    try {
      const res = await servicesApi.list()
      setServices(res.data || [])
    } catch (err) {
      message.error('获取服务列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchServices()
  }, [])

  const handleRegister = async () => {
    if (!name.trim() || !url.trim()) {
      message.warning('请填写服务名称和Swagger URL')
      return
    }
    try {
      await servicesApi.register({ name: name.trim(), spec_url: url.trim() })
      message.success('注册成功')
      setName('')
      setUrl('')
      fetchServices()
    } catch (err) {
      const msg = err?.response?.data?.detail || err.message || '未知错误'
      message.error(`注册失败: ${msg}`)
    }
  }

  const columns = [
    { title: '服务名称', dataIndex: 'name', key: 'name' },
    { title: '接口数量', dataIndex: 'operation_count', key: 'operation_count' },
    { title: 'Base URL', dataIndex: 'base_url', key: 'base_url' },
  ]

  return (
    <Space direction="vertical" style={{ display: 'flex' }} size="large">
      <Card title="注册Swagger服务">
        <Space direction="vertical" style={{ display: 'flex' }}>
          <Input
            placeholder="服务名称（如 kyc）"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <Input
            placeholder="Swagger URL"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          <Button type="primary" onClick={handleRegister}>
            注册
          </Button>
        </Space>
      </Card>

      <Card title="已注册服务">
        <Table
          rowKey="id"
          columns={columns}
          dataSource={services}
          loading={loading}
          pagination={false}
        />
      </Card>
    </Space>
  )
}

export default ServiceManager
