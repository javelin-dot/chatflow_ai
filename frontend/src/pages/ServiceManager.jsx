import React, { useState, useEffect } from 'react'
import { Card, Input, Button, Table, message, Space, Popconfirm } from 'antd'
import { EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { servicesApi } from '../api/client.js'

function ServiceManager() {
  const [name, setName] = useState('')
  const [url, setUrl] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [editingService, setEditingService] = useState(null)
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

  const resetForm = () => {
    setName('')
    setUrl('')
    setBaseUrl('')
    setEditingService(null)
  }

  const handleRegister = async () => {
    if (!name.trim() || !url.trim()) {
      message.warning('请填写服务名称和Swagger URL')
      return
    }
    try {
      const payload = {
        name: name.trim(),
        spec_url: url.trim(),
        base_url: baseUrl.trim() || undefined,
      }
      await servicesApi.register(payload)
      message.success(editingService ? '更新成功' : '注册成功')
      resetForm()
      fetchServices()
    } catch (err) {
      const msg = err?.response?.data?.detail || err.message || '未知错误'
      message.error(`${editingService ? '更新' : '注册'}失败: ${msg}`)
    }
  }

  const handleEdit = (record) => {
    setEditingService(record.name)
    setName(record.name)
    // We don't have the original spec_url stored in the list response,
    // so the user needs to re-enter it when editing.
    setUrl('')
    setBaseUrl(record.base_url || '')
  }

  const handleDelete = async (serviceName) => {
    try {
      await servicesApi.remove(serviceName)
      message.success('删除成功')
      if (editingService === serviceName) {
        resetForm()
      }
      fetchServices()
    } catch (err) {
      const msg = err?.response?.data?.detail || err.message || '未知错误'
      message.error(`删除失败: ${msg}`)
    }
  }

  const columns = [
    { title: '服务名称', dataIndex: 'name', key: 'name' },
    { title: '接口数量', dataIndex: 'operation_count', key: 'operation_count' },
    { title: 'Base URL', dataIndex: 'base_url', key: 'base_url' },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space>
          <Button
            icon={<EditOutlined />}
            size="small"
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确认删除"
            description={`确定要删除服务 "${record.name}" 吗？`}
            onConfirm={() => handleDelete(record.name)}
            okText="删除"
            cancelText="取消"
          >
            <Button icon={<DeleteOutlined />} size="small" danger>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <Space direction="vertical" style={{ display: 'flex' }} size="large">
      <Card title={editingService ? `编辑服务: ${editingService}` : '注册Swagger服务'}>
        <Space direction="vertical" style={{ display: 'flex' }}>
          <Input
            placeholder="服务名称（如 kyc）"
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={!!editingService}
          />
          <Input
            placeholder="Swagger URL"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          <Input
            placeholder="Base URL（可选，覆盖spec中的服务器地址）"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
          />
          <Space>
            <Button type="primary" onClick={handleRegister}>
              {editingService ? '保存修改' : '注册'}
            </Button>
            {editingService && (
              <Button onClick={resetForm}>取消</Button>
            )}
          </Space>
        </Space>
      </Card>

      <Card title="已注册服务">
        <Table
          rowKey="name"
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
