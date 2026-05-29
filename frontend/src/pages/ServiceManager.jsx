import React, { useState, useEffect } from 'react'
import { Card, Input, Button, Table, message, Space, Popconfirm, Modal } from 'antd'
import { EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { servicesApi } from '../api/client.js'

function ServiceManager() {
  const [name, setName] = useState('')
  const [url, setUrl] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [editModalVisible, setEditModalVisible] = useState(false)
  const [editName, setEditName] = useState('')
  const [editUrl, setEditUrl] = useState('')
  const [editBaseUrl, setEditBaseUrl] = useState('')
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

  const resetRegisterForm = () => {
    setName('')
    setUrl('')
    setBaseUrl('')
  }

  const resetEditForm = () => {
    setEditName('')
    setEditUrl('')
    setEditBaseUrl('')
    setEditModalVisible(false)
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
      message.success('注册成功')
      resetRegisterForm()
      fetchServices()
    } catch (err) {
      const msg = err?.response?.data?.detail || err.message || '未知错误'
      message.error(`注册失败: ${msg}`)
    }
  }

  const handleEdit = (record) => {
    setEditName(record.name)
    setEditUrl('')
    setEditBaseUrl(record.base_url || '')
    setEditModalVisible(true)
  }

  const handleEditSave = async () => {
    if (!editUrl.trim()) {
      message.warning('请填写Swagger URL')
      return
    }
    try {
      const payload = {
        name: editName,
        spec_url: editUrl.trim(),
        base_url: editBaseUrl.trim() || undefined,
      }
      await servicesApi.register(payload)
      message.success('更新成功')
      resetEditForm()
      fetchServices()
    } catch (err) {
      const msg = err?.response?.data?.detail || err.message || '未知错误'
      message.error(`更新失败: ${msg}`)
    }
  }

  const handleDelete = async (serviceName) => {
    try {
      await servicesApi.remove(serviceName)
      message.success('删除成功')
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
          <Input
            placeholder="Base URL（可选，覆盖spec中的服务器地址）"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
          />
          <Button type="primary" onClick={handleRegister}>
            注册
          </Button>
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

      <Modal
        title={`编辑服务: ${editName}`}
        open={editModalVisible}
        onOk={handleEditSave}
        onCancel={resetEditForm}
        okText="保存"
        cancelText="取消"
      >
        <Space direction="vertical" style={{ display: 'flex', width: '100%' }}>
          <Input
            placeholder="服务名称"
            value={editName}
            disabled
          />
          <Input
            placeholder="Swagger URL"
            value={editUrl}
            onChange={(e) => setEditUrl(e.target.value)}
          />
          <Input
            placeholder="Base URL（可选，覆盖spec中的服务器地址）"
            value={editBaseUrl}
            onChange={(e) => setEditBaseUrl(e.target.value)}
          />
        </Space>
      </Modal>
    </Space>
  )
}

export default ServiceManager
