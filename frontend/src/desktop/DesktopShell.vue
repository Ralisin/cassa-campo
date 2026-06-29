<script setup>
import { onMounted, ref } from 'vue'

import { usePolling } from '@/composables/usePolling'
import { useAppChrome } from '@/composables/useAppChrome'
import SidebarNav from '@/desktop/components/SidebarNav.vue'
import Topbar from '@/desktop/components/Topbar.vue'

const chrome = useAppChrome()
const {
  online,
  needRefresh,
  offlineQueue,
  pushError,
  loadNotifications,
  loadReimbursementCount,
  syncOfflineQueue,
  refreshPushState,
  updateApp,
} = chrome

const COLLAPSE_KEY = 'dk_sidebar_collapsed'
const collapsed = ref(localStorage.getItem(COLLAPSE_KEY) === '1')

function toggleSidebar() {
  collapsed.value = !collapsed.value
  localStorage.setItem(COLLAPSE_KEY, collapsed.value ? '1' : '0')
}

onMounted(async () => {
  await refreshPushState().catch(() => {})
  await loadNotifications().catch(() => {})
  await loadReimbursementCount().catch(() => {})
})
usePolling(loadNotifications, 15000)
usePolling(loadReimbursementCount, 7000)
usePolling(syncOfflineQueue, 20000)
</script>

<template>
  <div class="dk-shell" :class="{ 'dk-shell--collapsed': collapsed }">
    <aside class="dk-sidebar">
      <SidebarNav :collapsed="collapsed" @toggle="toggleSidebar" />
    </aside>

    <div class="dk-main">
      <Topbar :collapsed="collapsed" @toggle-sidebar="toggleSidebar" />

      <main class="dk-content">
        <div v-if="needRefresh" class="dk-banner dk-banner--update">
          <i class="pi pi-download" />
          <div class="dk-banner__copy">
            <strong>Nuova versione disponibile</strong>
            <span>Aggiorna per usare l'ultima versione del gestionale.</span>
          </div>
          <PButton label="Aggiorna" icon="pi pi-refresh" size="small" @click="updateApp" />
        </div>
        <div
          v-if="offlineQueue.pendingCount.value || !online"
          class="dk-banner"
          :class="online ? 'dk-banner--queue' : 'dk-banner--offline'"
        >
          <i :class="online ? 'pi pi-cloud-upload' : 'pi pi-wifi'" />
          <div class="dk-banner__copy">
            <strong>{{ online ? 'Coda offline' : 'Connessione assente' }}</strong>
            <span>
              {{ offlineQueue.pendingCount.value
                ? `${offlineQueue.pendingCount.value} movimenti in attesa di sincronizzazione`
                : 'I nuovi movimenti verranno salvati sul dispositivo.' }}
            </span>
          </div>
          <PButton
            v-if="online && offlineQueue.pendingCount.value"
            icon="pi pi-refresh"
            size="small"
            text
            :loading="offlineQueue.syncing.value"
            aria-label="Sincronizza"
            @click="syncOfflineQueue"
          />
        </div>
        <PMessage v-if="pushError" severity="warn" size="small" class="mb-3">{{ pushError }}</PMessage>

        <RouterView name="desktop" v-slot="{ Component }">
          <Transition name="dk-fade" mode="out-in">
            <component :is="Component" />
          </Transition>
        </RouterView>
      </main>
    </div>
  </div>
</template>
