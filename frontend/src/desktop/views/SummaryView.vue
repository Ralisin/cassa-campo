<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useConfirm } from 'primevue/useconfirm'
import { useRouter } from 'vue-router'

import { api, downloadExcel } from '@/api'
import { usePolling } from '@/composables/usePolling'
import ChartCard from '@/desktop/components/ChartCard.vue'
import KpiCard from '@/desktop/components/KpiCard.vue'
import PageHeader from '@/desktop/components/PageHeader.vue'
import { useSessionStore } from '@/stores/session'

const session = useSessionStore()
const router = useRouter()
const confirm = useConfirm()
const dashboard = ref(null)
const transfers = ref([])
const transferDialog = ref(false)
const savingTransfer = ref(false)
const deletingTransferId = ref(null)
const exportingReport = ref(false)
const transferError = ref('')
const transferActionError = ref('')
const editingTransferId = ref(null)
const euro = new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' })
const euroShort = new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })
const dateFormatter = new Intl.DateTimeFormat('it-IT', { day: '2-digit', month: 'short', year: '2-digit' })

const transfer = reactive({
  operation_date: new Date().toISOString().slice(0, 10),
  type: 'prelievo',
  amount: 0,
  notes: '',
})
const transferDate = computed({
  get: () => new Date(`${transfer.operation_date}T00:00:00`),
  set: (value) => {
    const year = value.getFullYear()
    const month = String(value.getMonth() + 1).padStart(2, '0')
    const day = String(value.getDate()).padStart(2, '0')
    transfer.operation_date = `${year}-${month}-${day}`
  },
})

const overviewKpis = computed(() => {
  const d = dashboard.value
  if (!d) return []
  return [
    { label: 'Spesa massima', value: euro.format(Number(d.max_budget)), icon: 'pi pi-briefcase', tone: 'forest' },
    { label: 'Spesa eseguita', value: euro.format(Number(d.spent)), icon: 'pi pi-receipt', tone: 'amber' },
    { label: 'Budget residuo', value: euro.format(Number(d.remaining_budget)), icon: 'pi pi-wallet', tone: 'emerald' },
    { label: 'Da rimborsare', value: euro.format(Number(d.pending_reimbursements ?? 0)), icon: 'pi pi-clock', tone: 'red' },
  ]
})
const methodKpis = computed(() => {
  const d = dashboard.value
  if (!d) return []
  return [
    { label: 'Contanti', value: euro.format(Number(d.cash_balance)), icon: 'pi pi-wallet', tone: 'emerald' },
    { label: 'Carta', value: euro.format(Number(d.bank_balance)), icon: 'pi pi-credit-card', tone: 'blue' },
  ]
})

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
  return { ...item, budget, spent, percentage: budget > 0 ? Math.min((spent / budget) * 100, 100) : 0, color: progressColor(spent, budget), overBudget: budget > 0 && spent > budget }
}))
const budgetChart = computed(() => ({
  data: {
    labels: categoryRows.value.map((row) => row.label),
    datasets: [
      { label: 'Preventivo', data: categoryRows.value.map((row) => row.budget), backgroundColor: 'rgba(120, 189, 152, 0.55)', borderRadius: 5, maxBarThickness: 30 },
      { label: 'Speso', data: categoryRows.value.map((row) => row.spent), backgroundColor: '#347d59', borderRadius: 5, maxBarThickness: 30 },
    ],
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, padding: 14 } }, tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: ${euro.format(ctx.parsed.y)}` } } },
    scales: { x: { grid: { display: false } }, y: { beginAtZero: true, ticks: { callback: (v) => euroShort.format(v) }, grid: { color: 'rgba(18,55,42,0.06)' } } },
  },
}))
const hasBudgetData = computed(() => categoryRows.value.some((row) => row.budget > 0 || row.spent > 0))

function formatDate(value) {
  return dateFormatter.format(new Date(`${value}T00:00:00`)).replace(/\./g, '')
}
function transferDirection(item) {
  return item.type === 'prelievo' ? 'Carta → Contanti' : 'Contanti → Carta'
}

async function loadDashboard() { dashboard.value = await api.get('/dashboard') }
async function loadTransfers() { transfers.value = await api.get('/transfers') }
async function loadSummary() { await Promise.all([loadDashboard(), loadTransfers()]) }

function openTransfer() {
  editingTransferId.value = null
  Object.assign(transfer, { operation_date: new Date().toISOString().slice(0, 10), type: 'prelievo', amount: 0, notes: '' })
  transferError.value = ''
  transferDialog.value = true
}
function editTransfer(item) {
  editingTransferId.value = item.id
  Object.assign(transfer, { operation_date: item.operation_date, type: item.type, amount: Number(item.amount), notes: item.notes })
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
    if (editingTransferId.value) await api.put(`/transfers/${editingTransferId.value}`, transfer)
    else await api.post('/transfers', transfer)
    await loadSummary()
    transferDialog.value = false
  } catch (cause) {
    transferError.value = cause instanceof Error ? cause.message : 'Giroconto non riuscito'
  } finally {
    savingTransfer.value = false
  }
}
function confirmRemoveTransfer(event, item) {
  confirm.require({
    target: event.currentTarget,
    message: `Eliminare il giroconto "${item.notes}"?`,
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Elimina',
    rejectLabel: 'Annulla',
    acceptClass: 'p-button-danger',
    accept: () => removeTransfer(item),
  })
}
async function removeTransfer(item) {
  transferActionError.value = ''
  deletingTransferId.value = item.id
  try {
    await api.delete(`/transfers/${item.id}`)
    await loadSummary()
  } catch (cause) {
    transferActionError.value = cause instanceof Error ? cause.message : 'Eliminazione non riuscita'
  } finally {
    deletingTransferId.value = null
  }
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
  <div v-if="dashboard">
    <PageHeader title="Riepilogo campo" subtitle="Bilancio, preventivi e giroconti">
      <template #actions>
        <PButton v-if="session.isOperator" label="Impostazioni" icon="pi pi-sliders-h" outlined @click="router.push('/impostazioni')" />
        <PButton v-if="session.isOperator" label="Esporta Excel" icon="pi pi-file-excel" class="dk-topbar__cta" :loading="exportingReport" @click="exportReport" />
      </template>
    </PageHeader>

    <div class="dk-grid dk-grid--kpi">
      <KpiCard v-for="kpi in overviewKpis" :key="kpi.label" v-bind="kpi" />
    </div>

    <div class="dk-grid dk-grid--dash dk-section">
      <ChartCard title="Preventivo vs Speso" subtitle="Confronto per categoria" icon="pi pi-chart-bar" :empty="!hasBudgetData" empty-text="Imposta i preventivi dalle impostazioni">
        <div style="height: 280px"><PChart type="bar" :data="budgetChart.data" :options="budgetChart.options" /></div>
      </ChartCard>

      <div class="dk-stack">
        <section class="dk-card">
          <h3 class="dk-card__title mb-4"><i class="pi pi-sliders-h dk-card__title-icon" /> Spesa per categoria</h3>
          <div v-if="hasBudgetData" class="space-y-4">
            <div v-for="row in categoryRows" :key="row.category">
              <div class="mb-1 flex items-center justify-between text-sm">
                <span class="font-bold capitalize">{{ row.label }}</span>
                <span class="font-semibold" :class="row.overBudget ? 'text-red-600' : 'text-slate-500'">
                  {{ euro.format(row.spent) }}<span class="text-slate-400"> / {{ row.budget > 0 ? euro.format(row.budget) : '—' }}</span>
                </span>
              </div>
              <div class="dk-progress"><span :style="{ width: `${row.percentage}%`, backgroundColor: row.color }" /></div>
            </div>
          </div>
          <p v-else class="dk-muted py-4 text-center text-sm">Nessun preventivo impostato.</p>
        </section>

        <div class="dk-grid dk-grid--2">
          <KpiCard v-for="kpi in methodKpis" :key="kpi.label" v-bind="kpi" />
        </div>
      </div>
    </div>

    <section class="dk-card dk-section">
      <header class="dk-card__head">
        <div>
          <h3 class="dk-card__title"><i class="pi pi-arrow-right-arrow-left dk-card__title-icon" /> Giroconti</h3>
          <p class="dk-card__subtitle">Spostamenti tra contanti e carta</p>
        </div>
        <PButton v-if="session.isOperator" label="Nuovo giroconto" icon="pi pi-plus" size="small" outlined @click="openTransfer" />
      </header>
      <PMessage v-if="transferActionError" severity="error" size="small" class="mb-3">{{ transferActionError }}</PMessage>

      <PDataTable :value="transfers" data-key="id" row-hover class="dk-table">
        <template #empty><div class="dk-table__empty"><i class="pi pi-arrow-right-arrow-left" /><span>Nessun giroconto registrato</span></div></template>
        <PColumn header="Data" style="width: 6.5rem"><template #body="{ data }"><span class="dk-table__date">{{ formatDate(data.operation_date) }}</span></template></PColumn>
        <PColumn header="Tipo" style="width: 9rem">
          <template #body="{ data }">
            <span class="dk-method">
              <i :class="data.type === 'prelievo' ? 'pi pi-money-bill' : 'pi pi-building-columns'" />
              <span class="capitalize">{{ data.type }}</span>
            </span>
          </template>
        </PColumn>
        <PColumn header="Direzione"><template #body="{ data }"><span class="text-sm text-slate-500">{{ transferDirection(data) }}</span></template></PColumn>
        <PColumn field="notes" header="Causale" />
        <PColumn header="Importo" style="width: 8rem" :pt="{ headerContent: { class: 'justify-end' } }">
          <template #body="{ data }"><span class="dk-amount" style="color: var(--dk-text)">{{ euro.format(Number(data.amount)) }}</span></template>
        </PColumn>
        <PColumn v-if="session.isOperator" header="" style="width: 6rem" :pt="{ headerContent: { class: 'justify-end' } }">
          <template #body="{ data }">
            <div class="dk-table__actions">
              <PButton icon="pi pi-pencil" text rounded size="small" aria-label="Modifica" @click="editTransfer(data)" />
              <PButton icon="pi pi-trash" text rounded size="small" severity="danger" aria-label="Elimina" :loading="deletingTransferId === data.id" @click="confirmRemoveTransfer($event, data)" />
            </div>
          </template>
        </PColumn>
      </PDataTable>
    </section>

    <PDialog v-model:visible="transferDialog" modal :header="editingTransferId ? 'Modifica giroconto' : 'Nuovo giroconto'" class="summary-dialog w-[28rem]">
      <form class="summary-dialog__form" @submit.prevent="saveTransfer">
        <div class="summary-dialog__field">
          <label>Tipo giroconto</label>
          <div class="exclusive-button-group">
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
  </div>
</template>
