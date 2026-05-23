import axios from 'axios'

const api = axios.create({ baseURL: '' })

export const getProviders = () => api.get('/providers')
export const testConnection = () => api.post('/test-connection')
export const updateConfig = (data) => api.post('/config', data)
export const createAgent = (data) => api.post('/agents/create', data)
export const chat = (data) => api.post('/agents/chat', data)
export const clearChatHistory = (agentDir) => api.delete('/agents/chat/history', { params: { agent_dir: agentDir } })
export const getBenchmark = (agentDir) => api.get('/agents/benchmark', { params: { agent_dir: agentDir } })
export const uploadDoc = (file, dir) => {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('target_dir', dir)
  return api.post('/documents/upload', fd)
}

export default api
