import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const kitsApi = {
  list: (params) => api.get('/kits', { params }).then(r => r.data),
  get: (id) => api.get(`/kits/${id}`).then(r => r.data),
  create: (data) => api.post('/kits', data).then(r => r.data),
  update: (id, data) => api.patch(`/kits/${id}`, data).then(r => r.data),
  delete: (id) => api.delete(`/kits/${id}`),
  uploadImage: (id, file) => {
    const form = new FormData()
    form.append('file', file)
    return api.post(`/kits/${id}/images`, form).then(r => r.data)
  },
  deleteImage: (kitId, imageId) => api.delete(`/kits/${kitId}/images/${imageId}`),
  filters: () => api.get('/kits/filters').then(r => r.data),
}

export const manualsApi = {
  get: (kitId) => api.get(`/kits/${kitId}/manual`).then(r => r.data),
  upload: (kitId, file) => {
    const form = new FormData()
    form.append('file', file)
    return api.post(`/kits/${kitId}/manual`, form).then(r => r.data)
  },
  delete: (kitId) => api.delete(`/kits/${kitId}/manual`),
}

export const scrapeApi = {
  startFull: (maxKits) => api.post('/scrape/start', { job_type: 'full_scrape', max_kits: maxKits }).then(r => r.data),
  startUpdate: () => api.post('/scrape/update').then(r => r.data),
  fetchManual: (kitId, bandaiManualId) =>
    api.post(`/scrape/manual/${kitId}?bandai_manual_id=${bandaiManualId}`).then(r => r.data),
  listJobs: (limit = 20) => api.get('/scrape/jobs', { params: { limit } }).then(r => r.data),
  getJob: (id) => api.get(`/scrape/jobs/${id}`).then(r => r.data),
}
