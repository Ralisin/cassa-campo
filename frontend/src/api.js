export const API_URL = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/+$/, '')

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
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
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
