<script setup>
import { computed, onMounted, reactive, ref } from 'vue'

import { api, downloadExcel } from '@/api'
import { usePolling } from '@/composables/usePolling'
import { useSessionStore } from '@/stores/session'

const dashboard = ref(null)
const settingsDialog = ref(false)
const transferDialog = ref(false)
const savingSettings = ref(false)
const savingTransfer = ref(false)
const exportingReport = ref(false)
const settingsError = ref('')
const transferError = ref('')
const transfers = ref([])
const session = useSessionStore()
const euro = new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' })
const settings = reactive({
  camp_year: new Date().getFullYear(),
  camp_name: 'Campo',
  participants: 0,
  quota_per_person: 0,
  cash_initial: 0,
})
const calculatedBudget = computed(() => Number(settings.participants) * Number(settings.quota_per_person))
const calculatedBankInitial = computed(() => calculatedBudget.value - Number(settings.cash_initial))
const transfer = reactive({
  operation_date: new Date().toISOString().slice(0, 10),
  type: 'prelievo',
  amount: 0,
  notes: '',
})
const summaryRows = computed(() => (dashboard.value ? [
  { icon: 'pi pi-briefcase', label: 'Spesa massima', value: dashboard.value.max_budget, tone: 'forest' },
  { icon: 'pi pi-receipt', label: 'Spesa eseguita', value: dashboard.value.spent, tone: 'blue' },
  { icon: 'pi pi-wallet', label: 'Budget residuo', value: dashboard.value.remaining_budget, tone: 'amber' },
] : []))
const methodRows = computed(() => (dashboard.value ? [
  { icon: 'pi pi-wallet', label: 'Contanti', value: dashboard.value.cash_balance, tone: 'emerald' },
  { icon: 'pi pi-credit-card', label: 'Carta', value: dashboard.value.bank_balance, tone: 'blue' },
] : []))
const latestTransfers = computed(() => transfers.value.slice(0, 5))
const transferDate = computed({
  get: () => new Date(`${transfer.operation_date}T00:00:00`),
  set: (value) => {
    const year = value.getFullYear()
    const month = String(value.getMonth() + 1).padStart(2, '0')
    const day = String(value.getDate()).padStart(2, '0')
    transfer.operation_date = `${year}-${month}-${day}`
  },
})

async function loadDashboard() {
  dashboard.value = await api.get('/dashboard')
}

async function loadTransfers() {
  transfers.value = await api.get('/transfers')
}

async function openSettings() {
  settingsError.value = ''
  try {
    Object.assign(settings, await api.get('/settings'))
  } catch (cause) {
    if (cause?.status !== 404) {
      settingsError.value = cause instanceof Error ? cause.message : 'Caricamento non riuscito'
    }
  }
  settingsDialog.value = true
}

async function saveInitialBalances() {
  savingSettings.value = true
  settingsError.value = ''
  try {
    await api.put('/settings', settings)
    await loadDashboard()
    settingsDialog.value = false
  } catch (cause) {
    settingsError.value = cause instanceof Error ? cause.message : 'Salvataggio non riuscito'
  } finally {
    savingSettings.value = false
  }
}

function openTransfer() {
  Object.assign(transfer, {
    operation_date: new Date().toISOString().slice(0, 10),
    type: 'prelievo',
    amount: 0,
    notes: '',
  })
  transferError.value = ''
  transferDialog.value = true
}

async function saveTransfer() {
  transferError.value = ''
  if (Number(transfer.amount) <= 0 || !transfer.notes.trim()) {
    transferError.value = 'Inserisci importo e causale del giroconto.'
    return
  }
  savingTransfer.value = true
  try {
    await api.post('/transfers', transfer)
    await Promise.all([loadDashboard(), loadTransfers()])
    transferDialog.value = false
  } catch (cause) {
    transferError.value = cause instanceof Error ? cause.message : 'Giroconto non riuscito'
  } finally {
    savingTransfer.value = false
  }
}

function transferDirection(item) {
  return item.type === 'prelievo' ? 'Carta -> Contanti' : 'Contanti -> Carta'
}

async function loadSummary() {
  await Promise.all([loadDashboard(), loadTransfers()])
}

async function exportReport() {
  exportingReport.value = true
  try {
    await downloadExcel()
  } finally {
    exportingReport.value = false
  }
}

onMounted(loadSummary)
usePolling(loadSummary)
</script>

<template>
  <main v-if="dashboard" class="summary-page">
    <section class="summary-section">
      <div class="summary-section-header">
        <h2 class="section-title">Riepilogo generale</h2>
      </div>
      <PCard class="summary-list-card">
        <template #content>
          <div class="summary-list">
            <div
              v-for="item in summaryRows"
              :key="item.label"
              class="summary-row"
            >
              <PAvatar :icon="item.icon" size="large" shape="square" class="summary-row__icon" :class="`summary-row__icon--${item.tone}`" />
              <span class="summary-row__label">{{ item.label }}</span>
              <span class="summary-row__value">{{ euro.format(Number(item.value)) }}</span>
            </div>
          </div>
        </template>
      </PCard>
    </section>

    <section class="summary-section">
      <div class="summary-section-header summary-section-header--split">
        <h2 class="section-title">Per metodo</h2>
        <div v-if="session.isAdmin" class="summary-actions">
          <PButton label="Giroconto" icon="pi pi-arrow-right-arrow-left" size="small" text class="summary-action" @click="openTransfer" />
          <PButton label="Dati campo e saldi" icon="pi pi-pencil" size="small" text class="summary-action" @click="openSettings" />
        </div>
      </div>
      <PCard class="summary-list-card">
        <template #content>
          <div class="summary-list">
            <div
              v-for="item in methodRows"
              :key="item.label"
              class="summary-row"
            >
              <PAvatar :icon="item.icon" size="large" shape="square" class="summary-row__icon" :class="`summary-row__icon--${item.tone}`" />
              <span class="summary-row__label">{{ item.label }}</span>
              <span class="summary-row__value">{{ euro.format(Number(item.value)) }}</span>
            </div>
          </div>
        </template>
      </PCard>
    </section>

    <section class="summary-section">
      <div class="summary-section-header">
        <h2 class="section-title">Ultimi giroconti</h2>
      </div>
      <PCard v-if="latestTransfers.length" class="summary-list-card">
        <template #content>
          <div class="summary-list">
            <div v-for="item in latestTransfers" :key="item.id" class="summary-row summary-transfer-row">
              <PAvatar
                :icon="item.type === 'prelievo' ? 'pi pi-arrow-down-left' : 'pi pi-arrow-up-right'"
                size="large"
                shape="square"
                class="summary-row__icon"
                :class="item.type === 'prelievo' ? 'summary-row__icon--emerald' : 'summary-row__icon--blue'"
              />
              <div class="summary-transfer-copy">
                <p class="summary-transfer-copy__title">{{ item.type }}</p>
                <p class="summary-transfer-copy__meta">{{ transferDirection(item) }} · {{ item.notes }}</p>
              </div>
              <span class="summary-row__value summary-row__value--small">{{ euro.format(Number(item.amount)) }}</span>
            </div>
          </div>
        </template>
      </PCard>
      <PCard v-else class="summary-empty-card">
        <template #content>
          <div class="summary-empty-state">
            <PAvatar icon="pi pi-arrow-right-arrow-left" shape="square" class="summary-row__icon summary-row__icon--slate" />
            <p>Nessun giroconto registrato.</p>
          </div>
        </template>
      </PCard>
    </section>

    <section v-if="session.isAdmin" class="summary-section">
      <div class="summary-section-header">
        <h2 class="section-title">Esportazione</h2>
      </div>
      <PCard class="summary-list-card">
        <template #content>
          <div class="summary-export-row">
            <PAvatar icon="pi pi-file-excel" size="large" shape="square" class="summary-row__icon summary-row__icon--forest" />
            <div class="summary-export-copy">
              <p class="summary-export-copy__title">Report completo</p>
              <p class="summary-export-copy__meta">File Excel (.xlsx)</p>
            </div>
            <PButton
              label="Scarica"
              icon="pi pi-download"
              size="small"
              class="summary-export-button"
              :loading="exportingReport"
              @click="exportReport"
            />
          </div>
        </template>
      </PCard>
    </section>

    <PDialog v-model:visible="settingsDialog" modal header="Imposta dati campo e saldi" class="summary-dialog w-[calc(100vw-2rem)] max-w-md">
      <form class="summary-dialog__form" @submit.prevent="saveInitialBalances">
        <p class="summary-dialog__intro">
          <i class="pi pi-info-circle" />
          Definisci quota campo, partecipanti e contanti iniziali. Il saldo carta viene calcolato automaticamente.
        </p>
        <div class="summary-dialog__field">
          <label for="participants">Numero paganti</label>
          <PInputNumber id="participants" v-model="settings.participants" :min="0" :use-grouping="false" fluid />
        </div>
        <div class="summary-dialog__field">
          <label for="quota-per-person">Quota campo a ragazzo</label>
          <PInputNumber id="quota-per-person" v-model="settings.quota_per_person" mode="currency" currency="EUR" locale="it-IT" :min="0" fluid />
        </div>
        <div class="summary-dialog__field">
          <label for="cash-initial">Contanti iniziali</label>
          <PInputNumber id="cash-initial" v-model="settings.cash_initial" mode="currency" currency="EUR" locale="it-IT" :min="0" :max="calculatedBudget" fluid />
        </div>
        <div class="summary-dialog__intro summary-dialog__intro--transfer">
          <i class="pi pi-calculator" />
          Spesa massima: {{ euro.format(calculatedBudget) }} · Carta iniziale: {{ euro.format(calculatedBankInitial) }}
        </div>
        <PMessage v-if="settingsError" severity="error" size="small">{{ settingsError }}</PMessage>
        <div class="summary-dialog__actions">
          <PButton type="button" label="Annulla" class="summary-dialog__cancel" @click="settingsDialog = false" />
          <PButton type="submit" label="Salva saldi" icon="pi pi-check" class="summary-dialog__submit" :loading="savingSettings" />
        </div>
      </form>
    </PDialog>

    <PDialog v-model:visible="transferDialog" modal header="Nuovo giroconto" class="summary-dialog w-[calc(100vw-2rem)] max-w-md">
      <form class="summary-dialog__form" @submit.prevent="saveTransfer">
        <div class="summary-dialog__field">
          <label>Tipo giroconto</label>
          <div class="exclusive-button-group summary-dialog__transfer-types">
            <PButton type="button" label="Prelievo" icon="pi pi-arrow-down-left" :class="{ 'exclusive-button--selected': transfer.type === 'prelievo' }" class="exclusive-button" @click="transfer.type = 'prelievo'" />
            <PButton type="button" label="Versamento" icon="pi pi-arrow-up-right" :class="{ 'exclusive-button--selected': transfer.type === 'versamento' }" class="exclusive-button" @click="transfer.type = 'versamento'" />
          </div>
          <p class="summary-dialog__intro summary-dialog__intro--transfer">
            <i :class="transfer.type === 'prelievo' ? 'pi pi-credit-card' : 'pi pi-wallet'" />
            {{ transfer.type === 'prelievo' ? 'Sposta denaro dalla carta ai contanti.' : 'Sposta denaro dai contanti alla carta.' }}
          </p>
        </div>
        <div class="summary-dialog__field"><label for="transfer-date">Data operazione</label><PDatePicker id="transfer-date" v-model="transferDate" date-format="dd/mm/yy" show-icon :manual-input="false" fluid /></div>
        <div class="summary-dialog__field"><label for="transfer-amount">Importo</label><PInputNumber id="transfer-amount" v-model="transfer.amount" mode="currency" currency="EUR" locale="it-IT" :min="0.01" fluid /></div>
        <div class="summary-dialog__field"><label for="transfer-notes">Causale</label><PInputText id="transfer-notes" v-model="transfer.notes" placeholder="Es. Prelievo ATM" fluid /></div>
        <PMessage v-if="transferError" severity="error" size="small">{{ transferError }}</PMessage>
        <div class="summary-dialog__actions">
          <PButton type="button" label="Annulla" class="summary-dialog__cancel" @click="transferDialog = false" />
          <PButton type="submit" label="Registra" icon="pi pi-check" class="summary-dialog__submit" :loading="savingTransfer" />
        </div>
      </form>
    </PDialog>
  </main>
</template>
