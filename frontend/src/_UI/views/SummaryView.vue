<script setup>
import { computed, onMounted, reactive, ref } from 'vue'

import { api, downloadExcel } from '@/api'
import { usePolling } from '@/composables/usePolling'
import { useSessionStore } from '@/stores/session'

const dashboard = ref(null)
const settingsDialog = ref(false)
const transferDialog = ref(false)
const categoriesExpanded = ref(false)
const cashExpanded = ref(false)
const transfersExpanded = ref(false)
const savingSettings = ref(false)
const savingTransfer = ref(false)
const deletingTransferId = ref(null)
const exportingReport = ref(false)
const settingsError = ref('')
const transferError = ref('')
const transferActionError = ref('')
const transfers = ref([])
const editingTransferId = ref(null)
const session = useSessionStore()
const euro = new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' })
const settings = reactive({
  camp_year: new Date().getFullYear(),
  camp_name: 'Campo',
  participants: 0,
  quota_per_person: 0,
  cash_initial: 0,
  category_budgets: {
    vitto: 0,
    alloggio: 0,
    trasporti: 0,
    varie: 0,
  },
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
  { icon: 'pi pi-receipt', label: 'Spesa eseguita', value: dashboard.value.spent, tone: 'blue', expandable: true },
  { icon: 'pi pi-wallet', label: 'Budget residuo', value: dashboard.value.remaining_budget, tone: 'amber' },
] : []))
const methodRows = computed(() => (dashboard.value ? [
  { icon: 'pi pi-wallet', label: 'Contanti', value: dashboard.value.cash_balance, tone: 'emerald', expandable: true },
  { icon: 'pi pi-credit-card', label: 'Carta', value: dashboard.value.bank_balance, tone: 'blue' },
] : []))
const cashDetails = computed(() => {
  const current = Number(dashboard.value?.cash_balance ?? 0)
  const pending = Number(dashboard.value?.pending_reimbursements ?? 0)
  return [
    { label: 'Attuali', value: current + pending },
    { label: 'Da rimborsare', value: pending },
    { label: 'Netti', value: current },
  ]
})
const visibleTransfers = computed(() => (
  transfersExpanded.value ? transfers.value : transfers.value.slice(0, 3)
))
const hiddenTransfersCount = computed(() => Math.max(transfers.value.length - 3, 0))
function progressColor(spent, budget) {
  if (budget <= 0) return '#94a3b8'
  const ratio = spent / budget
  if (ratio > 1) return '#dc2626'
  if (ratio <= 0.5) return `hsl(${140 - ratio * 60} 55% 38%)`
  if (ratio <= 0.8) return `hsl(${80 - ((ratio - 0.5) / 0.3) * 35} 75% 42%)`
  return `hsl(${45 - ((ratio - 0.8) / 0.2) * 25} 88% 48%)`
}

const categoryRows = computed(() => (dashboard.value?.category_summaries ?? []).map((item) => {
  const budget = Number(item.budget)
  const spent = Number(item.spent)
  return {
    ...item,
    budget,
    spent,
    percentage: budget > 0 ? Math.min((spent / budget) * 100, 100) : 0,
    progressColor: progressColor(spent, budget),
    overBudget: budget > 0 && spent > budget,
  }
}))
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
  editingTransferId.value = null
  Object.assign(transfer, {
    operation_date: new Date().toISOString().slice(0, 10),
    type: 'prelievo',
    amount: 0,
    notes: '',
  })
  transferError.value = ''
  transferDialog.value = true
}

function editTransfer(item) {
  editingTransferId.value = item.id
  Object.assign(transfer, {
    operation_date: item.operation_date,
    type: item.type,
    amount: Number(item.amount),
    notes: item.notes,
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
    if (editingTransferId.value) {
      await api.put(`/transfers/${editingTransferId.value}`, transfer)
    } else {
      await api.post('/transfers', transfer)
    }
    await Promise.all([loadDashboard(), loadTransfers()])
    transferDialog.value = false
  } catch (cause) {
    transferError.value = cause instanceof Error ? cause.message : 'Giroconto non riuscito'
  } finally {
    savingTransfer.value = false
  }
}

async function removeTransfer(item) {
  if (!window.confirm(`Eliminare il giroconto "${item.notes}"?`)) return
  transferActionError.value = ''
  deletingTransferId.value = item.id
  try {
    await api.delete(`/transfers/${item.id}`)
    await Promise.all([loadDashboard(), loadTransfers()])
  } catch (cause) {
    transferActionError.value = cause instanceof Error ? cause.message : 'Eliminazione non riuscita'
  } finally {
    deletingTransferId.value = null
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
            <template
              v-for="item in summaryRows"
              :key="item.label"
            >
              <button
                v-if="item.expandable"
                type="button"
                class="summary-row summary-row--expandable"
                :aria-expanded="categoriesExpanded"
                @click="categoriesExpanded = !categoriesExpanded"
              >
                <span class="summary-row__icon-wrap">
                  <PAvatar :icon="item.icon" size="large" shape="square" class="summary-row__icon" :class="`summary-row__icon--${item.tone}`" />
                  <span class="summary-row__expand-badge" :class="{ 'summary-row__expand-badge--expanded': categoriesExpanded }" />
                </span>
                <span class="summary-row__label">{{ item.label }}</span>
                <span class="summary-row__value">{{ euro.format(Number(item.value)) }}</span>
              </button>
              <div v-else class="summary-row">
                <PAvatar :icon="item.icon" size="large" shape="square" class="summary-row__icon" :class="`summary-row__icon--${item.tone}`" />
                <span class="summary-row__label">{{ item.label }}</span>
                <span class="summary-row__value">{{ euro.format(Number(item.value)) }}</span>
              </div>
              <Transition name="summary-submenu">
                <div v-if="item.expandable && categoriesExpanded" class="category-summary-submenu">
                  <p class="category-summary-subtitle">Spesa per categoria · eseguita su preventivo</p>
                  <div class="category-summary-list">
                    <div v-for="category in categoryRows" :key="category.category" class="category-summary-row">
                      <div class="category-summary-copy">
                        <strong>{{ category.label }}</strong>
                        <span>
                          {{ euro.format(category.spent) }}
                          <template v-if="category.budget > 0"> su {{ euro.format(category.budget) }}</template>
                          <template v-else> · preventivo non impostato</template>
                        </span>
                      </div>
                      <div class="category-progress" :class="{ 'category-progress--over': category.overBudget }">
                        <span :style="{ width: `${category.percentage}%`, backgroundColor: category.progressColor }" />
                      </div>
                    </div>
                  </div>
                </div>
              </Transition>
            </template>
          </div>
        </template>
      </PCard>
    </section>

    <section class="summary-section">
      <div class="summary-section-header summary-section-header--split">
        <h2 class="section-title">Per metodo</h2>
        <div v-if="session.isOperator" class="summary-actions">
          <PButton label="Dati campo e saldi" icon="pi pi-pencil" size="small" text class="summary-action" @click="openSettings" />
        </div>
      </div>
      <PCard class="summary-list-card">
        <template #content>
          <div class="summary-list">
            <template
              v-for="item in methodRows"
              :key="item.label"
            >
              <button
                v-if="item.expandable"
                type="button"
                class="summary-row summary-row--expandable"
                :aria-expanded="cashExpanded"
                @click="cashExpanded = !cashExpanded"
              >
                <span class="summary-row__icon-wrap">
                  <PAvatar :icon="item.icon" size="large" shape="square" class="summary-row__icon" :class="`summary-row__icon--${item.tone}`" />
                  <span class="summary-row__expand-badge" :class="{ 'summary-row__expand-badge--expanded': cashExpanded }" />
                </span>
                <span class="summary-row__label">{{ item.label }}</span>
                <span class="summary-row__value">{{ euro.format(Number(item.value)) }}</span>
              </button>
              <div v-else class="summary-row">
                <PAvatar :icon="item.icon" size="large" shape="square" class="summary-row__icon" :class="`summary-row__icon--${item.tone}`" />
                <span class="summary-row__label">{{ item.label }}</span>
                <span class="summary-row__value">{{ euro.format(Number(item.value)) }}</span>
              </div>
              <Transition name="summary-submenu">
                <div v-if="item.expandable && cashExpanded" class="cash-summary-submenu">
                  <div v-for="detail in cashDetails" :key="detail.label" class="cash-summary-detail">
                    <span>{{ detail.label }}</span>
                    <strong>{{ euro.format(detail.value) }}</strong>
                  </div>
                </div>
              </Transition>
            </template>
          </div>
        </template>
      </PCard>
    </section>

    <section class="summary-section">
      <div class="summary-section-header summary-section-header--split summary-section-header--transfers">
        <h2 class="section-title">Giroconti</h2>
        <PButton
          v-if="session.isOperator"
          label="Nuovo giroconto"
          icon="pi pi-plus"
          size="small"
          text
          class="summary-action"
          @click="openTransfer"
        />
      </div>
      <PMessage v-if="transferActionError" severity="error" size="small" class="summary-transfer-error">{{ transferActionError }}</PMessage>
      <PCard v-if="transfers.length" class="summary-list-card">
        <template #content>
          <div class="summary-list">
            <div v-for="item in visibleTransfers" :key="item.id" class="summary-row summary-transfer-row">
              <PAvatar
                :icon="item.type === 'prelievo' ? 'pi pi-money-bill' : 'pi pi-building-columns'"
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
              <div v-if="session.isOperator" class="summary-transfer-actions">
                <PButton
                  type="button"
                  icon="pi pi-pencil"
                  text
                  rounded
                  size="small"
                  aria-label="Modifica giroconto"
                  @click="editTransfer(item)"
                />
                <PButton
                  type="button"
                  icon="pi pi-trash"
                  text
                  rounded
                  size="small"
                  severity="danger"
                  aria-label="Elimina giroconto"
                  :loading="deletingTransferId === item.id"
                  @click="removeTransfer(item)"
                />
              </div>
            </div>
            <PButton
              v-if="hiddenTransfersCount > 0"
              type="button"
              :label="transfersExpanded ? 'Mostra meno' : `Mostra tutti (${transfers.length})`"
              :icon="transfersExpanded ? 'pi pi-chevron-up' : 'pi pi-chevron-down'"
              text
              class="summary-transfer-toggle"
              :aria-expanded="transfersExpanded"
              @click="transfersExpanded = !transfersExpanded"
            />
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

    <section v-if="session.isOperator" class="summary-section">
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

    <PDialog v-model:visible="settingsDialog" modal header="Imposta dati campo e saldi" class="summary-dialog summary-settings-dialog w-[calc(100vw-2rem)] max-w-2xl">
      <form class="summary-dialog__form summary-settings-dialog__form" @submit.prevent="saveInitialBalances">
        <p class="summary-dialog__intro">
          <i class="pi pi-info-circle" />
          Aggiorna i dati generali, i saldi iniziali e i preventivi usati nel riepilogo.
        </p>

        <section class="summary-settings-section">
          <div class="summary-settings-section__heading">
            <span class="summary-settings-section__icon"><i class="pi pi-calendar" /></span>
            <div>
              <strong>Dati del campo</strong>
              <p>Identificano il campo nei report esportati.</p>
            </div>
          </div>
          <div class="summary-settings-grid summary-settings-grid--camp">
            <div class="summary-dialog__field">
              <label for="camp-name">Nome campo</label>
              <PInputText id="camp-name" v-model="settings.camp_name" placeholder="Es. Campo estivo" fluid />
            </div>
            <div class="summary-dialog__field">
              <label for="camp-year">Anno</label>
              <PInputNumber id="camp-year" v-model="settings.camp_year" :min="2000" :max="2100" :use-grouping="false" fluid />
            </div>
          </div>
        </section>

        <section class="summary-settings-section">
          <div class="summary-settings-section__heading">
            <span class="summary-settings-section__icon"><i class="pi pi-wallet" /></span>
            <div>
              <strong>Partecipanti e saldi iniziali</strong>
              <p>La disponibilità su carta viene calcolata automaticamente.</p>
            </div>
          </div>
          <div class="summary-settings-grid summary-settings-grid--participants">
            <div class="summary-dialog__field">
              <label for="participants">Numero paganti</label>
              <PInputNumber id="participants" v-model="settings.participants" :min="0" :use-grouping="false" fluid />
            </div>
          </div>
          <div class="summary-settings-grid summary-settings-grid--balances">
            <div class="summary-dialog__field">
              <label for="quota-per-person">Quota per ragazzo</label>
              <PInputNumber id="quota-per-person" v-model="settings.quota_per_person" mode="currency" currency="EUR" locale="it-IT" :min="0" fluid />
            </div>
            <div class="summary-dialog__field">
              <label for="cash-initial">Contanti iniziali</label>
              <PInputNumber id="cash-initial" v-model="settings.cash_initial" mode="currency" currency="EUR" locale="it-IT" :min="0" :max="calculatedBudget" fluid />
            </div>
          </div>
        </section>

        <section class="summary-settings-section">
          <div class="summary-settings-section__heading">
            <span class="summary-settings-section__icon"><i class="pi pi-chart-bar" /></span>
            <div>
              <strong>Preventivo per categoria</strong>
              <p>Usato per confrontare graficamente preventivo e spesa eseguita.</p>
            </div>
          </div>
          <div class="summary-settings-grid summary-settings-grid--budgets">
            <div v-for="category in categoryRows" :key="category.category" class="summary-dialog__field">
              <label :for="`budget-${category.category}`">{{ category.label }}</label>
              <PInputNumber :id="`budget-${category.category}`" v-model="settings.category_budgets[category.category]" mode="currency" currency="EUR" locale="it-IT" :min="0" fluid />
            </div>
          </div>
        </section>

        <div class="summary-settings-totals">
          <div class="summary-settings-total">
            <span>Spesa massima</span>
            <strong>{{ euro.format(calculatedBudget) }}</strong>
          </div>
          <div class="summary-settings-total">
            <span>Carta iniziale</span>
            <strong>{{ euro.format(calculatedBankInitial) }}</strong>
          </div>
        </div>
        <PMessage v-if="settingsError" severity="error" size="small">{{ settingsError }}</PMessage>
        <div class="summary-dialog__actions">
          <PButton type="button" label="Annulla" class="summary-dialog__cancel" @click="settingsDialog = false" />
          <PButton type="submit" label="Salva saldi" icon="pi pi-check" class="summary-dialog__submit" :loading="savingSettings" />
        </div>
      </form>
    </PDialog>

    <PDialog v-model:visible="transferDialog" modal :header="editingTransferId ? 'Modifica giroconto' : 'Nuovo giroconto'" class="summary-dialog w-[calc(100vw-2rem)] max-w-md">
      <form class="summary-dialog__form" @submit.prevent="saveTransfer">
        <div class="summary-dialog__field">
          <label>Tipo giroconto</label>
          <div class="exclusive-button-group summary-dialog__transfer-types">
            <PButton type="button" label="Prelievo" icon="pi pi-money-bill" :class="{ 'exclusive-button--selected': transfer.type === 'prelievo' }" class="exclusive-button exclusive-button--prelievo" @click="transfer.type = 'prelievo'" />
            <PButton type="button" label="Versamento" icon="pi pi-building-columns" :class="{ 'exclusive-button--selected': transfer.type === 'versamento' }" class="exclusive-button exclusive-button--versamento" @click="transfer.type = 'versamento'" />
          </div>
          <p class="summary-dialog__intro summary-dialog__intro--transfer">
            <i :class="transfer.type === 'prelievo' ? 'pi pi-wallet' : 'pi pi-credit-card'" />
            {{ transfer.type === 'prelievo' ? 'Sposta denaro dalla carta ai contanti.' : 'Sposta denaro dai contanti alla carta.' }}
          </p>
        </div>
        <div class="summary-dialog__field"><label for="transfer-date">Data operazione</label><PDatePicker id="transfer-date" v-model="transferDate" date-format="dd/mm/yy" show-icon :manual-input="false" fluid /></div>
        <div class="summary-dialog__field"><label for="transfer-amount">Importo</label><PInputNumber id="transfer-amount" v-model="transfer.amount" mode="currency" currency="EUR" locale="it-IT" :min="0.01" fluid /></div>
        <div class="summary-dialog__field"><label for="transfer-notes">Causale</label><PInputText id="transfer-notes" v-model="transfer.notes" placeholder="Es. Prelievo ATM" fluid /></div>
        <PMessage v-if="transferError" severity="error" size="small">{{ transferError }}</PMessage>
        <div class="summary-dialog__actions">
          <PButton type="button" label="Annulla" class="summary-dialog__cancel" @click="transferDialog = false" />
          <PButton type="submit" :label="editingTransferId ? 'Salva modifiche' : 'Registra'" icon="pi pi-check" class="summary-dialog__submit" :loading="savingTransfer" />
        </div>
      </form>
    </PDialog>
  </main>
</template>
