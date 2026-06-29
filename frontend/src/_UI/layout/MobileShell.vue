<script setup>
import { computed, nextTick, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { usePolling } from '@/composables/usePolling'
import { useAppChrome } from '@/composables/useAppChrome'
import { useSessionStore } from '@/stores/session'

const session = useSessionStore()
const route = useRoute()
const router = useRouter()
const chrome = useAppChrome()

const {
  notifications,
  unreadCount,
  notificationsLoading,
  pendingReimbursementCount,
  online,
  needRefresh,
  offlineQueue,
  notificationCountLabel,
  reimbursementCountLabel,
  notificationIcon,
  formatNotificationDate,
  loadNotifications,
  loadReimbursementCount,
  syncOfflineQueue,
  markAllRead,
  updateApp,
} = chrome

const userMenu = ref()
const notificationsPopover = ref()

const ROLE_LABELS = { admin: 'Admin', cashier: 'Cassiere', user: 'Utente' }
const KIND_LABELS = { campo: 'Campo', anno: 'Anno' }
const userMenuItems = computed(() => [
  ...(session.canManageCasse
    ? [{ label: 'Casse', icon: 'pi pi-wallet', command: () => router.push('/seleziona-cassa') }]
    : session.memberships.length > 1
      ? [{ label: 'Cambia cassa', icon: 'pi pi-sync', command: () => router.push('/seleziona-cassa') }]
      : []),
  ...(session.isSystemAdmin
    ? [{ label: 'Console sistema', icon: 'pi pi-shield', command: () => router.push('/system') }]
    : []),
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

const navItems = computed(() => {
  const needsCassa = session.needsSystemCassaSelection
  return [
    ...(session.isSystemAdmin ? [{ label: 'Sistema', icon: 'pi pi-shield', to: '/system', key: 'system' }] : []),
    { label: 'Home', icon: 'pi pi-home', to: '/', key: 'home' },
    { label: 'Inserisci', icon: 'pi pi-plus', to: '/movimenti/nuovo', key: 'new' },
    { label: 'Movimenti', icon: 'pi pi-list', to: '/movimenti', key: 'movements' },
    { label: 'Rimborsi', icon: 'pi pi-replay', to: '/rimborsi', key: 'reimbursements' },
    { label: 'Riepilogo', icon: 'pi pi-chart-pie', to: '/riepilogo', key: 'summary' },
    ...(session.isAdmin ? [{ label: 'Utenti', icon: 'pi pi-users', to: '/utenti', key: 'users' }] : []),
  ].map((item) => ({
    ...item,
    disabled: (needsCassa && item.key !== 'system') || (session.cassaClosed && item.key === 'new'),
  }))
})
const activeNavIndex = computed(() => Math.max(
  navItems.value.findIndex((item) => item.key === route.meta.nav),
  0,
))
const pageDirection = ref('forward')
const navMotion = ref('idle')
let navMotionTimer
const pageTransitionName = computed(() => `menu-page-${pageDirection.value}`)
const offlineQueueLabel = computed(() => {
  if (!offlineQueue.pendingCount.value) return ''
  const label = offlineQueue.pendingCount.value === 1 ? 'movimento in attesa' : 'movimenti in attesa'
  if (!online.value) return `${offlineQueue.pendingCount.value} ${label} · offline`
  if (offlineQueue.syncing.value) return `Sincronizzazione di ${offlineQueue.pendingCount.value} ${label}`
  return `${offlineQueue.pendingCount.value} ${label} da sincronizzare`
})

async function toggleNotifications(event) {
  notificationsPopover.value.toggle(event)
  await loadNotifications()
}

async function openNotification(notification) {
  notificationsPopover.value.hide()
  await chrome.openNotification(notification, router)
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
      navMotionTimer = window.setTimeout(() => (navMotion.value = 'idle'), 450)
    })
  },
  { flush: 'sync' },
)

onMounted(async () => {
  await loadNotifications().catch(() => {})
  await loadReimbursementCount().catch(() => {})
})
onBeforeUnmount(() => {
  window.clearTimeout(navMotionTimer)
})
usePolling(loadNotifications, 15000)
usePolling(loadReimbursementCount, 7000)
usePolling(syncOfflineQueue, 20000)
</script>

<template>
  <div class="mx-auto min-h-screen max-w-3xl bg-[#f6f8f5] pb-24">
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
                <div v-if="session.activeCassa" class="mt-2 flex flex-wrap items-center gap-1.5">
                  <PTag :value="ROLE_LABELS[session.activeCassa.role] ?? session.activeCassa.role" severity="success" />
                  <PTag :value="session.activeCassa.unit" severity="info" />
                  <PTag :value="`${KIND_LABELS[session.activeCassa.kind] ?? session.activeCassa.kind} ${session.activeCassa.year}`" severity="warn" />
                  <PTag v-if="session.cassaClosed" value="Chiusa" severity="secondary" />
                  <PTag :value="session.activeCassa.group_name" severity="secondary" />
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
      <template #center>
        <div class="text-center">
          <h1 class="text-base font-black leading-tight text-slate-900">{{ route.meta.title }}</h1>
          <p v-if="session.activeCassa" class="text-[10px] font-bold uppercase tracking-wide text-slate-400">
            {{ session.activeCassa.group_name }} · {{ session.activeCassa.unit }} · {{ KIND_LABELS[session.activeCassa.kind] ?? session.activeCassa.kind }} {{ session.activeCassa.year }}<template v-if="session.cassaClosed"> · chiusa</template>
          </p>
        </div>
      </template>
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
      <div v-if="needRefresh" class="app-update-banner">
        <span class="app-update-banner__icon">
          <i class="pi pi-download" />
        </span>
        <span class="min-w-0 flex-1">
          <strong>Nuova versione disponibile</strong>
          <small>Aggiorna ora per usare l'ultima versione dell'app.</small>
        </span>
        <PButton
          label="Aggiorna"
          icon="pi pi-refresh"
          size="small"
          class="app-update-banner__button"
          @click="updateApp"
        />
      </div>
      <div
        v-if="offlineQueue.pendingCount.value || !online"
        class="offline-sync-banner"
        :class="{ 'offline-sync-banner--offline': !online }"
      >
        <span class="offline-sync-banner__icon">
          <i :class="online ? 'pi pi-cloud-upload' : 'pi pi-wifi'" />
        </span>
        <span class="min-w-0 flex-1">
          <strong>{{ online ? 'Coda offline' : 'Connessione assente' }}</strong>
          <small>{{ offlineQueueLabel || 'I nuovi movimenti verranno salvati sul dispositivo.' }}</small>
          <small v-if="offlineQueue.lastSyncError.value" class="offline-sync-banner__error">
            {{ offlineQueue.lastSyncError.value }}
          </small>
        </span>
        <PButton
          v-if="online && offlineQueue.pendingCount.value"
          icon="pi pi-refresh"
          rounded
          text
          :loading="offlineQueue.syncing.value"
          aria-label="Sincronizza movimenti offline"
          class="offline-sync-banner__button"
          @click="syncOfflineQueue"
        />
      </div>
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
      <component
        :is="item.disabled ? 'span' : RouterLink"
        v-for="item in navItems"
        :key="item.key"
        :to="item.disabled ? undefined : item.to"
        class="mobile-tabbar__item"
        :class="{
          'mobile-tabbar__item--active': route.meta.nav === item.key,
          'mobile-tabbar__item--disabled': item.disabled,
        }"
        :aria-disabled="item.disabled ? 'true' : undefined"
      >
        <PButton
          :icon="item.icon"
          rounded
          :text="route.meta.nav !== item.key"
          :aria-label="item.label"
          :disabled="item.disabled"
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
      </component>
    </nav>
  </div>
</template>
