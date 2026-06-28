import { readonly, ref } from 'vue'

import { api, uploadReceipt } from '@/api'

const DB_NAME = 'cassa-campo-offline'
const DB_VERSION = 1
const MOVEMENTS_STORE = 'movements'

const pendingCount = ref(0)
const syncing = ref(false)
const lastSyncError = ref('')
let dbPromise

function openDatabase() {
  if (dbPromise) return dbPromise
  dbPromise = new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION)

    request.onupgradeneeded = () => {
      const db = request.result
      if (!db.objectStoreNames.contains(MOVEMENTS_STORE)) {
        const store = db.createObjectStore(MOVEMENTS_STORE, { keyPath: 'id' })
        store.createIndex('createdAt', 'createdAt')
      }
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
  return dbPromise
}

async function withStore(mode, callback) {
  const db = await openDatabase()
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(MOVEMENTS_STORE, mode)
    const store = transaction.objectStore(MOVEMENTS_STORE)
    const result = callback(store)

    transaction.oncomplete = () => resolve(result)
    transaction.onerror = () => reject(transaction.error)
    transaction.onabort = () => reject(transaction.error)
  })
}

function requestToPromise(request) {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

async function loadQueuedMovements() {
  const items = await withStore('readonly', (store) => requestToPromise(store.getAll()))
  return items.sort((a, b) => a.createdAt.localeCompare(b.createdAt))
}

async function deleteQueuedMovement(id) {
  await withStore('readwrite', (store) => store.delete(id))
  await refreshPendingCount()
}

async function updateQueuedMovement(item) {
  await withStore('readwrite', (store) => store.put(item))
  await refreshPendingCount()
}

export async function refreshPendingCount() {
  pendingCount.value = await withStore('readonly', (store) => requestToPromise(store.count()))
  return pendingCount.value
}

export async function queueMovement(payload, receipts = [], userId = null, cassaId = null) {
  const item = {
    id: crypto.randomUUID(),
    createdAt: new Date().toISOString(),
    userId,
    cassaId,
    payload: { ...payload },
    receipts: receipts.map((file) => ({
      id: crypto.randomUUID(),
      file,
      name: file.name,
      size: file.size,
      type: file.type,
    })),
    savedMovementId: null,
    uploadedReceiptIds: [],
    lastError: '',
  }
  await withStore('readwrite', (store) => store.add(item))
  await refreshPendingCount()
  return item
}

export async function syncQueuedMovements(currentUserId = null) {
  if (syncing.value || !localStorage.getItem('access_token') || !navigator.onLine) {
    return { synced: 0, remaining: pendingCount.value }
  }

  syncing.value = true
  lastSyncError.value = ''
  let synced = 0

  try {
    const items = await loadQueuedMovements()
    for (const item of items) {
      if (item.userId && currentUserId && item.userId !== currentUserId) {
        lastSyncError.value = 'Ci sono movimenti offline salvati da un altro profilo su questo dispositivo.'
        continue
      }

      try {
        const cassaOptions = item.cassaId ? { cassaId: item.cassaId } : {}
        let movementId = item.savedMovementId
        if (!movementId) {
          const saved = await api.post('/movements', item.payload, cassaOptions)
          movementId = saved.id
          item.savedMovementId = movementId
          await updateQueuedMovement(item)
        }

        const uploaded = new Set(item.uploadedReceiptIds)
        for (const receipt of item.receipts) {
          if (uploaded.has(receipt.id)) continue
          await uploadReceipt(movementId, receipt.file, cassaOptions)
          uploaded.add(receipt.id)
          item.uploadedReceiptIds = Array.from(uploaded)
          await updateQueuedMovement(item)
        }

        await deleteQueuedMovement(item.id)
        synced += 1
      } catch (cause) {
        item.lastError = cause instanceof Error ? cause.message : 'Sincronizzazione non riuscita'
        await updateQueuedMovement(item)
        lastSyncError.value = item.lastError
        break
      }
    }
  } finally {
    await refreshPendingCount()
    syncing.value = false
  }

  return { synced, remaining: pendingCount.value }
}

export function useOfflineQueue() {
  return {
    pendingCount: readonly(pendingCount),
    syncing: readonly(syncing),
    lastSyncError: readonly(lastSyncError),
    queueMovement,
    refreshPendingCount,
    syncQueuedMovements,
  }
}
