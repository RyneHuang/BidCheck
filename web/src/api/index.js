import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const api = axios.create({
  baseURL: `${API_BASE}/api/v1`,
  timeout: 60000,
})

export async function createAnalysis(projectName, bidderFiles) {
  const formData = new FormData()
  const bidderNames = bidderFiles.map(b => b.name)
  formData.append('bidder_names', JSON.stringify(bidderNames))
  formData.append('project_name', projectName)

  bidderFiles.forEach(bidder => {
    bidder.files.forEach(file => {
      formData.append('files', file)
    })
  })

  const response = await api.post('/analyze', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return response.data
}

export async function getTaskStatus(taskId) {
  const response = await api.get(`/status/${taskId}`)
  return response.data
}

export async function getReportDetail(taskId) {
  const response = await api.get(`/report/${taskId}`)
  return response.data
}

export function getDownloadUrl(taskId, format = 'html') {
  return `${API_BASE}/api/v1/download/${taskId}?format=${format}`
}

export async function pollTaskStatus(taskId, onProgress, interval = 2000) {
  return new Promise((resolve, reject) => {
    const poll = async () => {
      try {
        const status = await getTaskStatus(taskId)
        onProgress?.(status)

        if (status.status === 'completed') {
          resolve(status)
        } else if (status.status === 'failed') {
          reject(new Error(status.error || '分析失败'))
        } else {
          setTimeout(poll, interval)
        }
      } catch (error) {
        reject(error)
      }
    }
    poll()
  })
}
