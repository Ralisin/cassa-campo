function defaultApiUrl() {
  if (typeof window === 'undefined') return 'http://localhost:8000'
  return `${window.location.protocol}//${window.location.hostname}:8000`
}

function configuredApiUrl() {
  const configured = import.meta.env.VITE_API_URL
  if (!configured) return defaultApiUrl()
  const url = new URL(configured, window.location.origin)
  const frontendHost = window.location.hostname
  const localApiHost = ['localhost', '127.0.0.1', '::1'].includes(url.hostname)
  const remoteFrontend = !['localhost', '127.0.0.1', '::1'].includes(frontendHost)
  if (localApiHost && remoteFrontend) {
    url.hostname = frontendHost
  }
  return url.toString()
}

export const API_URL = configuredApiUrl().replace(/\/+$/, '')

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

function errorMessage(detail) {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((item) => {
      const field = item.loc?.at(-1)
      const labels = {
        amount: 'Importo',
        supplier: 'Fornitore',
        operation_date: 'Data operazione',
        notes: 'Note',
        category: 'Categoria',
        cash_initial: 'Contanti iniziali',
      }
      return `${labels[field] ?? field ?? 'Dato'}: ${item.msg}`
    }).join('. ')
  }
  return 'Operazione non riuscita'
}

async function request(path, options = {}) {
  const token = localStorage.getItem('access_token')
  const jsonBody = options.body && !(options.body instanceof FormData)
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      ...(jsonBody ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new ApiError(errorMessage(body?.detail), response.status)
  }
  if (response.status === 204) return undefined
  return response.json()
}

export const api = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: 'POST', body: JSON.stringify(body) }),
  put: (path, body) => request(path, { method: 'PUT', body: JSON.stringify(body) }),
  delete: (path) => request(path, { method: 'DELETE' }),
}

export async function uploadReceipt(movementId, file) {
  const body = new FormData()
  body.append('file', file)
  return request(`/movements/${movementId}/receipts`, { method: 'POST', body, headers: {} })
}

export async function downloadReceipt(movementId, receipt) {
  const { url } = await api.get(`/movements/${movementId}/receipts/${receipt.id}`)
  const link = document.createElement('a')
  link.href = url
  link.download = receipt.filename
  link.target = '_blank'
  link.rel = 'noopener'
  link.click()
}

export async function downloadExcel() {
  const response = await fetch(`${API_URL}/exports/excel`, {
    headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
  })
  if (!response.ok) throw new ApiError('Esportazione non riuscita', response.status)
  const url = URL.createObjectURL(await response.blob())
  const link = document.createElement('a')
  link.href = url
  link.download = 'bilancio-campo.xlsx'
  link.click()
  URL.revokeObjectURL(url)
}
