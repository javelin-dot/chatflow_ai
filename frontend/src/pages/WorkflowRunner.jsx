import React, { useEffect, useState } from 'react'
import {
  Card,
  Select,
  Button,
  Spin,
  Tag,
  Collapse,
  Alert,
  Space,
  message,
} from 'antd'
import { PlayCircleOutlined } from '@ant-design/icons'
import { workflowsApi, runsApi } from '../api/client.js'

const { Option } = Select
const { Panel } = Collapse

function WorkflowRunner() {
  const [workflows, setWorkflows] = useState([])
  const [selectedWorkflow, setSelectedWorkflow] = useState('')
  const [running, setRunning] = useState(false)
  const [runResult, setRunResult] = useState(null)

  useEffect(() => {
    workflowsApi
      .list()
      .then((res) => {
        setWorkflows(res.data || [])
      })
      .catch(() => {
        message.error('加载流程列表失败')
      })
  }, [])

  const handleRun = async () => {
    if (!selectedWorkflow) {
      message.warning('请先选择一个流程')
      return
    }
    setRunning(true)
    setRunResult(null)
    try {
      const runRes = await workflowsApi.run(selectedWorkflow)
      const { run_id } = runRes.data
      // Poll for run result
      let result = null
      for (let i = 0; i < 30; i++) {
        await new Promise((r) => setTimeout(r, 1000))
        const statusRes = await runsApi.get(run_id)
        result = statusRes.data
        if (result.status === 'success' || result.status === 'failed') {
          break
        }
      }
      setRunResult(result)
      if (result && result.status === 'success') {
        message.success('流程执行成功')
      } else if (result && result.status === 'failed') {
        message.error('流程执行失败')
      } else {
        message.warning('流程执行超时或状态未知')
      }
    } catch (err) {
      message.error('运行流程失败')
    } finally {
      setRunning(false)
    }
  }

  const statusColor = (status) => {
    if (status === 'success') return 'green'
    if (status === 'failed') return 'red'
    return 'default'
  }

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Card title="执行流程">
        <Space>
          <Select
            placeholder="选择流程"
            style={{ width: 300 }}
            value={selectedWorkflow || undefined}
            onChange={(value) => setSelectedWorkflow(value)}
          >
            {workflows.map((wf) => (
              <Option key={wf.id} value={wf.id}>
                {wf.name}
              </Option>
            ))}
          </Select>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            loading={running}
            onClick={handleRun}
          >
            运行
          </Button>
        </Space>
      </Card>

      {running && !runResult && (
        <Spin tip="流程执行中...">
          <div style={{ minHeight: 120 }} />
        </Spin>
      )}

      {runResult && (
        <Card title="执行结果">
          <Space direction="vertical" style={{ width: '100%' }}>
            <div>
              <strong>run_id:</strong> {runResult.run_id}
            </div>
            <div>
              <strong>status:</strong>{' '}
              <Tag color={statusColor(runResult.status)}>
                {runResult.status}
              </Tag>
            </div>

            <Collapse style={{ width: '100%' }}>
              {Object.entries(runResult.step_results || {}).map(
                ([stepId, step]) => (
                  <Panel
                    header={
                      <Space>
                        <Tag color={statusColor(step.status)}>
                          {step.status}
                        </Tag>
                        <span>{stepId}</span>
                      </Space>
                    }
                    key={stepId}
                  >
                    <Space direction="vertical" style={{ width: '100%' }}>
                      {step.error && (
                        <Alert
                          message="错误"
                          description={step.error}
                          type="error"
                          showIcon
                        />
                      )}
                      <div>
                        <strong>Request:</strong>
                        <pre
                          style={{
                            background: '#f6f8fa',
                            padding: 12,
                            borderRadius: 4,
                            overflow: 'auto',
                          }}
                        >
                          {JSON.stringify(step.request, null, 2)}
                        </pre>
                      </div>
                      <div>
                        <strong>Response:</strong>
                        <pre
                          style={{
                            background: '#f6f8fa',
                            padding: 12,
                            borderRadius: 4,
                            overflow: 'auto',
                          }}
                        >
                          {JSON.stringify(step.response, null, 2)}
                        </pre>
                      </div>
                    </Space>
                  </Panel>
                )
              )}
            </Collapse>
          </Space>
        </Card>
      )}
    </Space>
  )
}

export default WorkflowRunner
