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
  const { cassaId, ...fetchOptions } = options
  const token = localStorage.getItem('access_token')
  // Default to the active cassa; callers (e.g. the offline queue) may override it.
  const cassa = cassaId ?? localStorage.getItem('active_cassa_id')
  const jsonBody = fetchOptions.body && !(fetchOptions.body instanceof FormData)
  const response = await fetch(`${API_URL}${path}`, {
    ...fetchOptions,
    headers: {
      ...(jsonBody ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(cassa ? { 'X-Cassa-Id': cassa } : {}),
      ...fetchOptions.headers,
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
  get: (path, options = {}) => request(path, options),
  post: (path, body, options = {}) => request(path, { method: 'POST', body: JSON.stringify(body), ...options }),
  put: (path, body, options = {}) => request(path, { method: 'PUT', body: JSON.stringify(body), ...options }),
  delete: (path, options = {}) => request(path, { method: 'DELETE', ...options }),
}

export async function uploadReceipt(movementId, file, options = {}) {
  const body = new FormData()
  body.append('file', await compressReceiptFile(file))
  return request(`/movements/${movementId}/receipts`, { method: 'POST', body, headers: {}, ...options })
}

export async function compressReceiptFile(file) {
  if (!file.type.startsWith('image/') || file.type === 'image/png') return file
  if (typeof document === 'undefined' || typeof createImageBitmap === 'undefined') return file

  try {
    const bitmap = await createImageBitmap(file)
    const maxSide = 1800
    const ratio = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height))
    if (ratio >= 1 && file.size < 1_200_000) return file
    const canvas = document.createElement('canvas')
    canvas.width = Math.max(1, Math.round(bitmap.width * ratio))
    canvas.height = Math.max(1, Math.round(bitmap.height * ratio))
    const ctx = canvas.getContext('2d')
    ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.82))
    if (!blob || blob.size >= file.size) return file
    return new File([blob], file.name.replace(/\.[^.]+$/, '.jpg'), { type: 'image/jpeg' })
  } catch {
    return file
  }
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
  const cassaId = localStorage.getItem('active_cassa_id')
  const response = await fetch(`${API_URL}/exports/excel`, {
    headers: {
      Authorization: `Bearer ${localStorage.getItem('access_token')}`,
      ...(cassaId ? { 'X-Cassa-Id': cassaId } : {}),
    },
  })
  if (!response.ok) throw new ApiError('Esportazione non riuscita', response.status)
  const disposition = response.headers.get('Content-Disposition') || ''
  const filename = disposition.match(/filename="([^"]+)"/)?.[1] || 'bilancio.xlsx'
  const url = URL.createObjectURL(await response.blob())
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}
