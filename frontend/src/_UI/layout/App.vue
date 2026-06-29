<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRegisterSW } from 'virtual:pwa-register/vue'
import { useRoute, useRouter } from 'vue-router'

import { useAppChrome } from '@/composables/useAppChrome'
import { useViewport } from '@/composables/useViewport'
import { useSessionStore } from '@/stores/session'
import DesktopShell from '@/desktop/DesktopShell.vue'
import MobileShell from '@/_UI/layout/MobileShell.vue'

const session = useSessionStore()
const route = useRoute()
const router = useRouter()
const chrome = useAppChrome()
const { isDesktop } = useViewport()
const { needRefresh, updateServiceWorker } = useRegisterSW()

// Bridge the PWA service-worker state into the shared chrome composable so both
// shells can show the "update available" banner and trigger an update.
watch(needRefresh, (value) => { chrome.needRefresh.value = value }, { immediate: true })
chrome.setUpdater(updateServiceWorker)

const showShell = computed(() => route.path !== '/login' && !route.meta.cassaSelect)

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

const installButtonLabel = computed(() => isIos ? 'Ho capito' : 'Installa ora')
const installButtonIcon = computed(() => isIos ? 'pi pi-check' : 'pi pi-download')

function canShowInstallDialog() {
  // The native install prompt only makes sense on touch / mobile contexts.
  if (isDesktop.value || isInstalled()) return false
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

function handleOnline() {
  chrome.online.value = true
  chrome.syncOfflineQueue()
}

function handleOffline() {
  chrome.online.value = false
}

onMounted(async () => {
  window.addEventListener('beforeinstallprompt', captureInstallPrompt)
  window.addEventListener('appinstalled', handleAppInstalled)
  window.addEventListener('online', handleOnline)
  window.addEventListener('offline', handleOffline)
  if (isIos) scheduleInstallDialog()

  if (session.authenticated && !session.user) {
    await session.loadUser().catch(() => {
      session.logout()
      router.push('/login')
    })
  }
  await chrome.offlineQueue.refreshPendingCount().catch(() => {})
  await chrome.syncOfflineQueue()
})
onBeforeUnmount(() => {
  window.clearTimeout(installDialogTimer)
  window.removeEventListener('beforeinstallprompt', captureInstallPrompt)
  window.removeEventListener('appinstalled', handleAppInstalled)
  window.removeEventListener('online', handleOnline)
  window.removeEventListener('offline', handleOffline)
})
</script>

<template>
  <template v-if="showShell">
    <DesktopShell v-if="isDesktop" />
    <MobileShell v-else />
  </template>
  <RouterView v-else :name="isDesktop ? 'desktop' : undefined" />

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

  <PConfirmDialog class="dk-confirm" />
</template>
