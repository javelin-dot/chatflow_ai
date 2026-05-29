import React, { useState, useEffect } from 'react'
import {
  Card,
  Input,
  Select,
  Button,
  Space,
  Tag,
  Divider,
  message,
} from 'antd'
import {
  PlusOutlined,
  DeleteOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
} from '@ant-design/icons'
import { servicesApi, workflowsApi } from '../api/client.js'

function WorkflowBuilder() {
  const [workflowName, setWorkflowName] = useState('')
  const [selectedService, setSelectedService] = useState('')
  const [services, setServices] = useState([])
  const [operations, setOperations] = useState({}) // { [serviceId]: [ops] }
  const [steps, setSteps] = useState([])

  useEffect(() => {
    const fetchServices = async () => {
      try {
        const res = await servicesApi.list()
        setServices(res.data || [])
      } catch (err) {
        message.error('获取服务列表失败')
      }
    }
    fetchServices()
  }, [])

  useEffect(() => {
    if (!selectedService) return
    if (operations[selectedService]) return

    const fetchOperations = async () => {
      try {
        const res = await servicesApi.getOperations(selectedService)
        setOperations((prev) => ({
          ...prev,
          [selectedService]: res.data || [],
        }))
      } catch (err) {
        message.error('获取接口列表失败')
      }
    }
    fetchOperations()
  }, [selectedService, operations])

  const addStep = () => {
    const newStep = {
      id: `step_${steps.length + 1}`,
      name: '',
      operation_id: '',
      parameter_mapping: {},
      save_response_to: '',
    }
    setSteps([...steps, newStep])
  }

  const removeStep = (index) => {
    const newSteps = steps.filter((_, i) => i !== index)
    setSteps(newSteps)
  }

  const moveStep = (index, direction) => {
    if (direction === 'up' && index === 0) return
    if (direction === 'down' && index === steps.length - 1) return
    const newSteps = [...steps]
    const swapIndex = direction === 'up' ? index - 1 : index + 1
    ;[newSteps[index], newSteps[swapIndex]] = [
      newSteps[swapIndex],
      newSteps[index],
    ]
    setSteps(newSteps)
  }

  const updateStep = (index, key, value) => {
    const newSteps = [...steps]
    newSteps[index] = { ...newSteps[index], [key]: value }
    setSteps(newSteps)
  }

  const getOperationById = (operationId) => {
    const ops = operations[selectedService] || []
    return ops.find((op) => op.operation_id === operationId)
  }

  const handleSave = async () => {
    if (!workflowName.trim()) {
      message.warning('请填写流程名称')
      return
    }
    if (!selectedService) {
      message.warning('请选择服务')
      return
    }
    if (steps.length === 0) {
      message.warning('请至少添加一个步骤')
      return
    }
    for (const step of steps) {
      if (!step.operation_id) {
        message.warning('请为每个步骤选择接口')
        return
      }
    }

    const payload = {
      id: `wf-${Date.now()}`,
      name: workflowName.trim(),
      service_id: selectedService,
      steps: steps.map((step) => ({
        id: step.id,
        name: step.name || undefined,
        operation_id: step.operation_id,
        parameter_mapping: step.parameter_mapping,
        save_response_to: step.save_response_to || undefined,
      })),
    }

    try {
      await workflowsApi.create(payload)
      message.success('流程保存成功')
      setWorkflowName('')
      setSelectedService('')
      setSteps([])
    } catch (err) {
      const msg = err?.response?.data?.detail || err.message || '未知错误'
      message.error(`保存失败: ${msg}`)
    }
  }

  const serviceOptions = services.map((s) => ({
    value: s.name,
    label: s.name,
  }))

  const operationOptions =
    operations[selectedService]?.map((op) => ({
      value: op.operation_id,
      label: `${op.method} ${op.path} — ${op.operation_id}`,
    })) || []

  return (
    <Space direction="vertical" style={{ display: 'flex' }} size="large">
      <Card title="流程基本信息">
        <Space direction="vertical" style={{ display: 'flex' }}>
          <Input
            placeholder="流程名称（如：创建KYC客户）"
            value={workflowName}
            onChange={(e) => setWorkflowName(e.target.value)}
          />
          <Select
            placeholder="选择服务"
            showSearch
            filterOption={(input, option) =>
              (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
            }
            value={selectedService || undefined}
            onChange={(value) => {
              setSelectedService(value)
              setSteps([])
            }}
            options={serviceOptions}
            style={{ width: '100%' }}
          />
        </Space>
      </Card>

      {steps.map((step, index) => {
        const op = getOperationById(step.operation_id)
        return (
          <Card
            key={step.id}
            title={`步骤 ${index + 1}: ${step.name || '未命名'}`}
            extra={
              <Space>
                <Button
                  icon={<ArrowUpOutlined />}
                  size="small"
                  onClick={() => moveStep(index, 'up')}
                  disabled={index === 0}
                />
                <Button
                  icon={<ArrowDownOutlined />}
                  size="small"
                  onClick={() => moveStep(index, 'down')}
                  disabled={index === steps.length - 1}
                />
                <Button
                  icon={<DeleteOutlined />}
                  size="small"
                  danger
                  onClick={() => removeStep(index)}
                />
              </Space>
            }
          >
            <Space direction="vertical" style={{ display: 'flex' }}>
              <Select
                placeholder="选择接口"
                showSearch
                filterOption={(input, option) =>
                  (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                }
                value={step.operation_id || undefined}
                onChange={(value) => {
                  const newMapping = {}
                  updateStep(index, 'operation_id', value)
                  updateStep(index, 'parameter_mapping', newMapping)
                }}
                options={operationOptions}
                style={{ width: '100%' }}
              />
              <Input
                placeholder="步骤名称（可选）"
                value={step.name}
                onChange={(e) => updateStep(index, 'name', e.target.value)}
              />
              {op?.parameters && op.parameters.length > 0 && (
                <>
                  <Divider orientation="left">参数映射</Divider>
                  <Space direction="vertical" style={{ display: 'flex' }}>
                    {op.parameters.map((param) => {
                      const mapping = step.parameter_mapping[param.name] || {
                        source: 'const',
                        value: '',
                      }
                      return (
                        <Space key={param.name} wrap>
                          <Tag>
                            {param.name}
                            {param.required && (
                              <span style={{ color: 'red' }}>*</span>
                            )}
                          </Tag>
                          <Tag color="default">
                            {param.in}/{param.type}
                          </Tag>
                          <Select
                            value={mapping.source}
                            onChange={(source) => {
                              const newMapping = {
                                ...step.parameter_mapping,
                                [param.name]: {
                                  ...mapping,
                                  source,
                                },
                              }
                              updateStep(
                                index,
                                'parameter_mapping',
                                newMapping
                              )
                            }}
                            options={[
                              { value: 'const', label: '常量' },
                              { value: 'context', label: '上下文' },
                            ]}
                            style={{ width: 100 }}
                          />
                          <Input
                            placeholder={
                              mapping.source === 'context'
                                ? '如：login_result.token'
                                : '值'
                            }
                            value={mapping.value}
                            onChange={(e) => {
                              const newMapping = {
                                ...step.parameter_mapping,
                                [param.name]: {
                                  ...mapping,
                                  value: e.target.value,
                                },
                              }
                              updateStep(
                                index,
                                'parameter_mapping',
                                newMapping
                              )
                            }}
                            style={{ width: 200 }}
                          />
                        </Space>
                      )
                    })}
                  </Space>
                </>
              )}
              <Input
                placeholder="保存响应到变量（如 login_result）"
                value={step.save_response_to}
                onChange={(e) =>
                  updateStep(index, 'save_response_to', e.target.value)
                }
              />
            </Space>
          </Card>
        )
      })}

      <Button block dashed icon={<PlusOutlined />} onClick={addStep}>
        添加步骤
      </Button>

      <Button type="primary" size="large" block onClick={handleSave}>
        保存流程
      </Button>
    </Space>
  )
}

export default WorkflowBuilder
