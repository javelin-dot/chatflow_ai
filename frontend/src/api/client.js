import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

export const servicesApi = {
  register: (data) => api.post('/services', data),
  list: () => api.get('/services'),
  remove: (serviceId) => api.delete(`/services/${serviceId}`),
  getOperations: (serviceId) => api.get(`/services/${serviceId}/operations`),
  getOperation: (serviceId, operationId) =>
    api.get(`/services/${serviceId}/operations/${operationId}`),
}

export const workflowsApi = {
  create: (data) => api.post('/workflows', data),
  list: () => api.get('/workflows'),
  get: (id) => api.get(`/workflows/${id}`),
  update: (id, data) => api.put(`/workflows/${id}`, data),
  remove: (id) => api.delete(`/workflows/${id}`),
  run: (id) => api.post(`/workflows/${id}/runs`),
}

export const runsApi = {
  get: (runId) => api.get(`/runs/${runId}`),
}

export const sessionsApi = {
  login: (data) => api.post('/sessions', data),
  clear: () => api.delete('/sessions'),
  get: () => api.get('/sessions'),
}

export default api
