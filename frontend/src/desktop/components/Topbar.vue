<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAppChrome } from '@/composables/useAppChrome'
import { useSessionStore } from '@/stores/session'

defineProps({ collapsed: { type: Boolean, default: false } })
defineEmits(['toggle-sidebar'])

const session = useSessionStore()
const route = useRoute()
const router = useRouter()
const chrome = useAppChrome()
const KIND_LABELS = { campo: 'Campo', anno: 'Anno' }
const {
  notifications,
  unreadCount,
  notificationsLoading,
  notificationCountLabel,
  notificationIcon,
  formatNotificationDate,
  loadNotifications,
  markAllRead,
} = chrome

const search = ref('')
const notificationsPopover = ref()

function submitSearch() {
  const term = search.value.trim()
  router.push(term ? { path: '/movimenti', query: { q: term } } : '/movimenti')
}

async function toggleNotifications(event) {
  notificationsPopover.value.toggle(event)
  await loadNotifications()
}

async function openNotification(notification) {
  notificationsPopover.value.hide()
  await chrome.openNotification(notification, router)
}
</script>

<template>
  <header class="dk-topbar">
    <div class="dk-topbar__title">
      <PButton
        v-if="route.meta.back"
        icon="pi pi-arrow-left"
        text
        rounded
        aria-label="Indietro"
        class="dk-topbar__back"
        @click="router.back()"
      />
      <div class="min-w-0">
        <h1 class="dk-topbar__heading">{{ route.meta.title }}</h1>
        <p v-if="session.activeCassa" class="dk-topbar__crumb">
          {{ session.activeCassa.group_name }} · {{ session.activeCassa.unit }} · {{ KIND_LABELS[session.activeCassa.kind] ?? session.activeCassa.kind }} {{ session.activeCassa.year }}<template v-if="session.cassaClosed"> · chiusa</template>
        </p>
      </div>
    </div>

    <div class="dk-topbar__actions">
      <div class="dk-topbar__bell">
        <PButton icon="pi pi-bell" text rounded aria-label="Notifiche" @click="toggleNotifications" />
        <span v-if="unreadCount" class="dk-topbar__bell-badge">{{ notificationCountLabel }}</span>
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

      <PButton
        label="Nuovo movimento"
        icon="pi pi-plus"
        class="dk-topbar__cta"
        @click="router.push('/movimenti/nuovo')"
      />
    </div>
  </header>
</template>
