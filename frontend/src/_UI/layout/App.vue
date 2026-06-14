<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '@/api'
import { usePolling } from '@/composables/usePolling'
import { useSessionStore } from '@/stores/session'

const session = useSessionStore()
const route = useRoute()
const router = useRouter()
const userMenu = ref()
const notificationsPopover = ref()
const notifications = ref([])
const unreadCount = ref(0)
const notificationsLoading = ref(false)
const pendingReimbursementCount = ref(0)
const installDialogVisible = ref(false)
const installPrompt = ref(null)
const installPromptPending = ref(false)
const installDismissedKey = 'install_prompt_dismissed_at'
const installDismissalDuration = 7 * 24 * 60 * 60 * 1000
let installDialogTimer
const isIos = /iPad|iPhone|iPod/.test(navigator.userAgent)
  || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
const isInstalled = () => window.matchMedia('(display-mode: standalone)').matches
  || window.navigator.standalone === true
const userMenuItems = computed(() => [
  { separator: true },
  {
    label: 'Esci',
    icon: 'pi pi-sign-out',
    command: () => {
      session.logout()
      router.push('/login')
    },
  },
])
const userInitials = computed(() => {
  const name = session.user?.name?.trim()
  if (!name) return 'CC'
  return name.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()
})

const navItems = computed(() => [
  { label: 'Home', icon: 'pi pi-home', to: '/', key: 'home' },
  { label: 'Inserisci', icon: 'pi pi-plus', to: '/movimenti/nuovo', key: 'new' },
  { label: 'Movimenti', icon: 'pi pi-list', to: '/movimenti', key: 'movements' },
  { label: 'Rimborsi', icon: 'pi pi-replay', to: '/rimborsi', key: 'reimbursements' },
  { label: 'Riepilogo', icon: 'pi pi-chart-pie', to: '/riepilogo', key: 'summary' },
  ...(session.isAdmin ? [{ label: 'Utenti', icon: 'pi pi-users', to: '/utenti', key: 'users' }] : []),
])
const activeNavIndex = computed(() => Math.max(
  navItems.value.findIndex((item) => item.key === route.meta.nav),
  0,
))
const pageDirection = ref('forward')
const navMotion = ref('idle')
let navMotionTimer
const pageTransitionName = computed(() => `menu-page-${pageDirection.value}`)
const notificationCountLabel = computed(() => unreadCount.value > 99 ? '99+' : String(unreadCount.value))
const reimbursementCountLabel = computed(() => (
  pendingReimbursementCount.value > 99 ? '99+' : String(pendingReimbursementCount.value)
))
const installButtonLabel = computed(() => isIos ? 'Ho capito' : 'Installa ora')
const installButtonIcon = computed(() => isIos ? 'pi pi-check' : 'pi pi-download')

function canShowInstallDialog() {
  if (isInstalled()) return false
  const dismissedAt = Number(localStorage.getItem(installDismissedKey))
  return !dismissedAt || Date.now() - dismissedAt > installDismissalDuration
}

function scheduleInstallDialog() {
  if (!canShowInstallDialog()) return
  window.clearTimeout(installDialogTimer)
  installDialogTimer = window.setTimeout(() => {
    installDialogVisible.value = true
  }, 1200)
}

function captureInstallPrompt(event) {
  event.preventDefault()
  installPrompt.value = event
  scheduleInstallDialog()
}

function dismissInstallDialog() {
  installDialogVisible.value = false
  localStorage.setItem(installDismissedKey, String(Date.now()))
}

async function installApp() {
  if (isIos) {
    dismissInstallDialog()
    return
  }
  if (!installPrompt.value) return

  installPromptPending.value = true
  try {
    await installPrompt.value.prompt()
    const { outcome } = await installPrompt.value.userChoice
    installPrompt.value = null
    installDialogVisible.value = false
    if (outcome === 'dismissed') {
      localStorage.setItem(installDismissedKey, String(Date.now()))
    }
  } finally {
    installPromptPending.value = false
  }
}

function handleAppInstalled() {
  installPrompt.value = null
  installDialogVisible.value = false
  localStorage.removeItem(installDismissedKey)
}

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

async function loadNotifications() {
  if (!session.authenticated || route.path === '/login') return
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
  if (!session.authenticated || route.path === '/login') return
  const result = await api.get('/reimbursements')
  pendingReimbursementCount.value = result.pending_count
}

async function toggleNotifications(event) {
  notificationsPopover.value.toggle(event)
  await loadNotifications()
}

async function openNotification(notification) {
  if (!notification.read_at) {
    await api.put(`/notifications/${notification.id}/read`)
  }
  notificationsPopover.value.hide()
  await loadNotifications()
  await router.push(notificationTarget(notification))
}

async function markAllRead() {
  await api.put('/notifications/read-all')
  await loadNotifications()
}

watch(
  () => route.meta.nav,
  (next, previous) => {
    const nextIndex = navItems.value.findIndex((item) => item.key === next)
    const previousIndex = navItems.value.findIndex((item) => item.key === previous)
    if (nextIndex === previousIndex) pageDirection.value = 'fade'
    else pageDirection.value = nextIndex > previousIndex ? 'forward' : 'backward'
    navMotion.value = nextIndex > previousIndex ? 'right' : nextIndex < previousIndex ? 'left' : 'idle'
    window.clearTimeout(navMotionTimer)
    nextTick(() => {
      navMotionTimer = window.setTimeout(() => (navMotion.value = 'idle'), 560)
    })
  },
  { flush: 'sync' },
)

onMounted(async () => {
  window.addEventListener('beforeinstallprompt', captureInstallPrompt)
  window.addEventListener('appinstalled', handleAppInstalled)
  if (isIos) scheduleInstallDialog()

  if (session.authenticated && !session.user) {
    await session.loadUser().catch(() => {
      session.logout()
      router.push('/login')
    })
  }
  await loadNotifications().catch(() => {})
  await loadReimbursementCount().catch(() => {})
})
onBeforeUnmount(() => {
  window.clearTimeout(installDialogTimer)
  window.removeEventListener('beforeinstallprompt', captureInstallPrompt)
  window.removeEventListener('appinstalled', handleAppInstalled)
})
usePolling(loadNotifications, 15000)
usePolling(loadReimbursementCount, 7000)
</script>

<template>
  <div v-if="route.path !== '/login'" class="mx-auto min-h-screen max-w-3xl bg-[#f6f8f5] pb-24">
    <PToolbar class="sticky top-0 z-30 !rounded-none !border-x-0 !border-t-0 !bg-white/95 !px-4 backdrop-blur">
      <template #start>
        <PButton v-if="route.meta.back" icon="pi pi-arrow-left" text rounded aria-label="Indietro" @click="router.back()" />
        <PButton v-else icon="pi pi-bars" text rounded aria-label="Menu utente" @click="userMenu.toggle($event)" />
        <PMenu ref="userMenu" :model="userMenuItems" popup class="user-menu">
          <template #start>
            <div class="user-menu__profile">
              <PAvatar :label="userInitials" size="large" shape="circle" class="!bg-forest !font-black !text-white" />
              <div class="min-w-0">
                <p class="truncate text-sm font-black text-slate-900">{{ session.user?.name ?? 'Utente' }}</p>
                <p class="mt-0.5 truncate text-xs text-slate-500">{{ session.user?.email }}</p>
                <div class="mt-2 flex items-center gap-1.5">
                  <PTag :value="session.user?.role ?? 'utente'" severity="secondary" class="capitalize" />
                  <PTag v-if="session.user?.branch" :value="session.user.branch" severity="info" />
                </div>
              </div>
            </div>
          </template>
          <template #item="{ item, props }">
            <a v-bind="props.action" class="user-menu__logout">
              <i :class="item.icon" /><span>{{ item.label }}</span>
            </a>
          </template>
        </PMenu>
      </template>
      <template #center><h1 class="text-center text-base font-black text-slate-900">{{ route.meta.title }}</h1></template>
      <template #end>
        <div class="notification-bell">
          <PButton icon="pi pi-bell" text rounded aria-label="Notifiche" @click="toggleNotifications" />
          <span v-if="unreadCount" class="notification-bell__badge">{{ notificationCountLabel }}</span>
        </div>
        <PPopover ref="notificationsPopover" class="notifications-popover">
          <div class="notifications-panel">
            <div class="notifications-panel__header">
              <div>
                <p class="text-sm font-black text-slate-900">Notifiche</p>
                <p class="text-xs text-slate-500">{{ unreadCount ? `${unreadCount} da leggere` : 'Sei al corrente di tutto' }}</p>
              </div>
              <PButton
                v-if="unreadCount"
                label="Segna lette"
                text
                size="small"
                class="notifications-panel__read-all"
                @click="markAllRead"
              />
            </div>

            <div v-if="notificationsLoading && !notifications.length" class="notifications-panel__empty">
              Caricamento notifiche...
            </div>
            <div v-else-if="!notifications.length" class="notifications-panel__empty">
              <i class="pi pi-bell-slash" />
              <span>Nessuna notifica per ora</span>
            </div>
            <template v-else>
              <button
                v-for="notification in notifications"
                :key="notification.id"
                type="button"
                class="notification-item"
                :class="{ 'notification-item--unread': !notification.read_at }"
                @click="openNotification(notification)"
              >
                <span class="notification-item__icon" :class="`notification-item__icon--${notification.kind}`">
                  <i :class="notificationIcon(notification.kind)" />
                </span>
                <span class="min-w-0 flex-1 text-left">
                  <span class="notification-item__title">{{ notification.title }}</span>
                  <span class="notification-item__message">{{ notification.message }}</span>
                  <span class="notification-item__date">{{ formatNotificationDate(notification.created_at) }}</span>
                </span>
                <span v-if="!notification.read_at" class="notification-item__dot" aria-label="Non letta" />
              </button>
            </template>
          </div>
        </PPopover>
      </template>
    </PToolbar>

    <div class="menu-page-shell px-4 py-5">
      <RouterView v-slot="{ Component, route: currentRoute }">
        <Transition :name="pageTransitionName" mode="out-in">
          <component :is="Component" :key="currentRoute.fullPath" />
        </Transition>
      </RouterView>
    </div>

    <nav
      class="mobile-tabbar"
      :class="`mobile-tabbar--moving-${navMotion}`"
      :style="{
        gridTemplateColumns: `repeat(${navItems.length}, minmax(0, 1fr))`,
        '--nav-count': navItems.length,
        '--active-offset': `${activeNavIndex * 100}%`,
      }"
    >
      <span class="mobile-tabbar__trail" aria-hidden="true" />
      <span class="mobile-tabbar__indicator" aria-hidden="true">
        <span class="mobile-tabbar__indicator-glow" />
        <span class="mobile-tabbar__indicator-surface" />
      </span>
      <RouterLink
        v-for="item in navItems"
        :key="item.key"
        :to="item.to"
        class="mobile-tabbar__item"
        :class="{ 'mobile-tabbar__item--active': route.meta.nav === item.key }"
      >
        <PButton
          :icon="item.icon"
          rounded
          :text="route.meta.nav !== item.key"
          :aria-label="item.label"
          class="mobile-tabbar__icon"
          :class="{ 'mobile-tabbar__icon--active': route.meta.nav === item.key }"
        />
        <span
          v-if="item.key === 'reimbursements' && pendingReimbursementCount"
          class="mobile-tabbar__badge"
          :aria-label="`${pendingReimbursementCount} rimborsi da fare`"
        >
          {{ reimbursementCountLabel }}
        </span>
        <span class="mobile-tabbar__label">{{ item.label }}</span>
      </RouterLink>
    </nav>
  </div>
  <RouterView v-else />

  <PDialog
    v-model:visible="installDialogVisible"
    modal
    :closable="false"
    :draggable="false"
    class="install-dialog w-[calc(100vw-2rem)] max-w-sm"
  >
    <div class="install-dialog__content">
      <div class="install-dialog__icon">
        <img src="/pwa-192x192.png" alt="" />
      </div>
      <div>
        <p class="install-dialog__eyebrow">Cassa Campo sul tuo dispositivo</p>
        <h2 class="install-dialog__title">Installa l'app</h2>
        <p v-if="!isIos" class="install-dialog__description">
          Aprila dalla schermata Home, a tutto schermo e sempre a portata di mano.
        </p>
        <div v-else class="install-dialog__ios-instructions">
          <p>Per installarla su iPhone o iPad:</p>
          <p><span>1</span> Tocca <i class="pi pi-upload" /> Condividi in Safari.</p>
          <p><span>2</span> Scegli <strong>Aggiungi alla schermata Home</strong>.</p>
        </div>
      </div>
      <div class="install-dialog__actions">
        <PButton label="Non ora" text class="install-dialog__later" @click="dismissInstallDialog" />
        <PButton
          :label="installButtonLabel"
          :icon="installButtonIcon"
          :loading="installPromptPending"
          class="install-dialog__install"
          @click="installApp"
        />
      </div>
    </div>
  </PDialog>
</template>
