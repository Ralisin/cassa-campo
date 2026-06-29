import { computed, ref } from 'vue'

import { api } from '@/api'
import { useOfflineQueue } from '@/offlineQueue'
import { useSessionStore } from '@/stores/session'

// Shared "app chrome" state — notifications, reimbursement badge, offline queue,
// PWA update/install — extracted from the old App.vue so both the mobile shell
// and the desktop shell can drive the same logic. State lives at module level so
// there is a single source of truth regardless of which shell is mounted.

const notifications = ref([])
const unreadCount = ref(0)
const notificationsLoading = ref(false)
const pendingReimbursementCount = ref(0)
const online = ref(typeof navigator === 'undefined' ? true : navigator.onLine)
const pushSupported = ref(false)
const pushEnabled = ref(false)
const pushBusy = ref(false)
const pushError = ref('')

// Populated by the root component (App.vue) which owns the SW registration.
// `needRefresh` is a writable ref the root keeps in sync with useRegisterSW.
const needRefresh = ref(false)
let updateServiceWorker = async () => {}

function setUpdater(updater) {
  updateServiceWorker = updater
}

const notificationCountLabel = computed(() => (unreadCount.value > 99 ? '99+' : String(unreadCount.value)))
const reimbursementCountLabel = computed(() => (
  pendingReimbursementCount.value > 99 ? '99+' : String(pendingReimbursementCount.value)
))

function notificationIcon(kind) {
  if (kind === 'reimbursement_completed') return 'pi pi-check-circle'
  if (kind === 'reimbursement_requested') return 'pi pi-replay'
  return 'pi pi-plus'
}

function notificationTarget(notification) {
  return notification.kind === 'reimbursement_completed'
    ? '/rimborsi'
    : `/movimenti/${notification.movement_id}`
}

function formatNotificationDate(value) {
  return new Intl.DateTimeFormat('it-IT', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

function notificationPermission() {
  if (typeof window === 'undefined' || !('Notification' in window)) return 'unsupported'
  return window.Notification.permission
}

function urlBase64ToUint8Array(value) {
  const padding = '='.repeat((4 - (value.length % 4)) % 4)
  const base64 = `${value}${padding}`.replace(/-/g, '+').replace(/_/g, '/')
  const raw = window.atob(base64)
  return Uint8Array.from([...raw].map((char) => char.charCodeAt(0)))
}

function subscriptionPayload(subscription) {
  const json = subscription.toJSON()
  return {
    endpoint: json.endpoint,
    keys: {
      p256dh: json.keys?.p256dh,
      auth: json.keys?.auth,
    },
  }
}

export function useAppChrome() {
  const session = useSessionStore()
  const offlineQueue = useOfflineQueue()

  async function loadNotifications() {
    if (!session.authenticated || !session.activeCassaId) return
    notificationsLoading.value = true
    try {
      const result = await api.get('/notifications')
      notifications.value = result.items
      unreadCount.value = result.unread_count
    } finally {
      notificationsLoading.value = false
    }
  }

  async function loadReimbursementCount() {
    if (!session.authenticated || !session.activeCassaId) return
    const result = await api.get('/reimbursements')
    pendingReimbursementCount.value = result.pending_count
  }

  async function syncOfflineQueue() {
    if (!session.authenticated) return
    await offlineQueue.syncQueuedMovements(session.user?.id).catch(() => {})
  }

  async function refreshPushState() {
    pushError.value = ''
    pushSupported.value = Boolean(
      typeof window !== 'undefined'
      && 'Notification' in window
      && 'serviceWorker' in navigator
      && 'PushManager' in window,
    )
    if (!pushSupported.value || !session.authenticated) {
      pushEnabled.value = false
      return
    }
    const registration = await navigator.serviceWorker.ready
    pushEnabled.value = Boolean(await registration.pushManager.getSubscription())
  }

  async function enablePushNotifications() {
    pushBusy.value = true
    pushError.value = ''
    try {
      await refreshPushState()
      if (!pushSupported.value) {
        pushError.value = 'Notifiche push non supportate su questo dispositivo.'
        return false
      }
      const { public_key: publicKey } = await api.get('/notifications/push-public-key')
      if (!publicKey) {
        pushError.value = 'Notifiche push non configurate sul server.'
        return false
      }
      if (notificationPermission() === 'denied') {
        pushError.value = 'Permesso notifiche negato nelle impostazioni del dispositivo.'
        return false
      }
      const permission = notificationPermission() === 'granted'
        ? 'granted'
        : await window.Notification.requestPermission()
      if (permission !== 'granted') {
        pushError.value = 'Permesso notifiche non concesso.'
        return false
      }

      const registration = await navigator.serviceWorker.ready
      let subscription = await registration.pushManager.getSubscription()
      if (!subscription) {
        subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(publicKey),
        })
      }
      await api.post('/notifications/push-subscriptions', subscriptionPayload(subscription))
      pushEnabled.value = true
      return true
    } catch (cause) {
      pushError.value = cause instanceof Error ? cause.message : 'Attivazione notifiche non riuscita'
      return false
    } finally {
      pushBusy.value = false
    }
  }

  async function disablePushNotifications() {
    pushBusy.value = true
    pushError.value = ''
    try {
      if (!pushSupported.value) return false
      const registration = await navigator.serviceWorker.ready
      const subscription = await registration.pushManager.getSubscription()
      if (subscription) {
        await api.post('/notifications/push-unsubscribe', subscriptionPayload(subscription)).catch(() => {})
        await subscription.unsubscribe()
      }
      pushEnabled.value = false
      return true
    } catch (cause) {
      pushError.value = cause instanceof Error ? cause.message : 'Disattivazione notifiche non riuscita'
      return false
    } finally {
      pushBusy.value = false
    }
  }

  async function markAllRead() {
    await api.put('/notifications/read-all')
    await loadNotifications()
  }

  async function openNotification(notification, router) {
    if (!notification.read_at) {
      await api.put(`/notifications/${notification.id}/read`)
    }
    await loadNotifications()
    await router.push(notificationTarget(notification))
  }

  async function updateApp() {
    await updateServiceWorker(true)
  }

  return {
    // state
    notifications,
    unreadCount,
    notificationsLoading,
    pendingReimbursementCount,
    online,
    pushSupported,
    pushEnabled,
    pushBusy,
    pushError,
    needRefresh,
    offlineQueue,
    // labels / helpers
    notificationCountLabel,
    reimbursementCountLabel,
    notificationIcon,
    formatNotificationDate,
    // actions
    loadNotifications,
    loadReimbursementCount,
    syncOfflineQueue,
    refreshPushState,
    enablePushNotifications,
    disablePushNotifications,
    markAllRead,
    openNotification,
    updateApp,
    setUpdater,
  }
}
