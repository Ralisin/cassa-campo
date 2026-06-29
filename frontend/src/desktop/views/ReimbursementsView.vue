<script setup>
import { computed, onMounted, ref } from 'vue'

import { api } from '@/api'
import { usePolling } from '@/composables/usePolling'
import KpiCard from '@/desktop/components/KpiCard.vue'
import PageHeader from '@/desktop/components/PageHeader.vue'
import { useSessionStore } from '@/stores/session'

const session = useSessionStore()
const summary = ref(null)
const statusFilter = ref('da_rimborsare')
const creatorFilter = ref('tutti')
const updating = ref(null)
const euro = new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' })
const dateFormatter = new Intl.DateTimeFormat('it-IT', { day: '2-digit', month: 'short', year: '2-digit' })
const dateTimeFormatter = new Intl.DateTimeFormat('it-IT', { dateStyle: 'medium', timeStyle: 'short' })

const statuses = [
  { label: 'Da rimborsare', value: 'da_rimborsare' },
  { label: 'Rimborsati', value: 'rimborsato' },
  { label: 'Tutti', value: 'tutti' },
]
const creators = computed(() => [
  { label: 'Tutte le persone', value: 'tutti' },
  ...Array.from(
    new Map(
      (summary.value?.movements ?? []).map((movement) => [
        movement.created_by,
        { label: movement.creator_name, value: movement.created_by },
      ]),
    ).values(),
  ).sort((a, b) => a.label.localeCompare(b.label, 'it')),
])
const filtered = computed(() => (summary.value?.movements ?? []).filter((movement) => (
  (statusFilter.value === 'tutti' || movement.reimbursement_status === statusFilter.value)
  && (creatorFilter.value === 'tutti' || movement.created_by === creatorFilter.value)
)))

const kpis = computed(() => {
  const s = summary.value
  if (!s) return []
  return [
    { label: session.isOperator ? 'Da restituire' : 'Ti devono restituire', value: euro.format(Number(s.pending_amount)), icon: 'pi pi-clock', tone: 'amber', hint: `${s.pending_count} movimenti` },
    { label: 'Già rimborsati', value: euro.format(Number(s.reimbursed_amount)), icon: 'pi pi-check-circle', tone: 'emerald', hint: `${s.reimbursed_count} movimenti` },
  ]
})

function formatDate(value) {
  return dateFormatter.format(new Date(`${value}T00:00:00`)).replace(/\./g, '')
}
function formatDateTime(value) {
  return dateTimeFormatter.format(new Date(value))
}

async function load() {
  summary.value = await api.get('/reimbursements')
}

async function toggle(movement) {
  updating.value = movement.id
  try {
    summary.value = await api.put(`/reimbursements/${movement.id}`, {
      reimbursed: movement.reimbursement_status !== 'rimborsato',
    })
  } finally {
    updating.value = null
  }
}

onMounted(load)
usePolling(load)
</script>

<template>
  <div>
    <PageHeader title="Rimborsi" subtitle="Spese anticipate da restituire" />

    <template v-if="!summary">
      <div class="dk-grid dk-grid--2" style="max-width: 40rem">
        <article v-for="n in 2" :key="n" class="dk-kpi">
          <Skel circle w="3rem" h="3rem" />
          <div class="dk-kpi__body" style="flex: 1"><Skel w="55%" h="0.7rem" /><Skel w="65%" h="1.5rem" r="0.5rem" class="mt-2" /></div>
        </article>
      </div>
      <div class="dk-card dk-section">
        <div class="dk-toolbar"><Skel w="11rem" h="2.4rem" /><Skel w="11rem" h="2.4rem" /></div>
        <div class="dk-skel-rows">
          <div v-for="n in 5" :key="n" class="dk-skel-row">
            <div style="flex: 1"><Skel w="35%" h="0.85rem" /><Skel w="22%" h="0.65rem" class="mt-1.5" /></div>
            <Skel w="5rem" h="0.8rem" />
            <Skel w="4.5rem" h="0.9rem" />
            <Skel v-if="session.isOperator" w="9rem" h="2rem" r="0.5rem" />
          </div>
        </div>
      </div>
    </template>

    <template v-else>
    <div class="dk-grid dk-grid--2" style="max-width: 40rem">
      <KpiCard v-for="kpi in kpis" :key="kpi.label" v-bind="kpi" />
    </div>

    <div class="dk-card dk-section">
      <div class="dk-toolbar">
        <PSelect v-model="statusFilter" :options="statuses" option-label="label" option-value="value" />
        <PSelect v-if="session.isOperator" v-model="creatorFilter" :options="creators" option-label="label" option-value="value" filter />
        <span class="dk-toolbar__spacer text-sm text-slate-400">{{ filtered.length }} risultati</span>
      </div>

      <PDataTable :value="filtered" data-key="id" row-hover class="dk-table">
        <template #empty>
          <div class="dk-table__empty"><i class="pi pi-check-circle" /><span>Nessun rimborso in questa sezione</span></div>
        </template>
        <PColumn header="Data" style="width: 6.5rem">
          <template #body="{ data }"><span class="dk-table__date">{{ formatDate(data.operation_date) }}</span></template>
        </PColumn>
        <PColumn field="supplier" header="Fornitore">
          <template #body="{ data }">
            <div class="min-w-0">
              <span class="dk-mv__name">{{ data.supplier }}</span>
              <span v-if="data.notes" class="dk-mv__notes">{{ data.notes }}</span>
            </div>
          </template>
        </PColumn>
        <PColumn header="Anticipato da">
          <template #body="{ data }"><span class="dk-table__creator"><i class="pi pi-user" />{{ data.creator_name }}</span></template>
        </PColumn>
        <PColumn header="Rimborsato il">
          <template #body="{ data }">
            <span v-if="data.reimbursed_at" class="text-xs text-slate-500">
              {{ formatDateTime(data.reimbursed_at) }}<template v-if="data.reimbursed_by_name"> · {{ data.reimbursed_by_name }}</template>
            </span>
            <span v-else class="dk-muted">—</span>
          </template>
        </PColumn>
        <PColumn header="Importo" style="width: 8rem" :pt="{ headerContent: { class: 'justify-end' } }">
          <template #body="{ data }">
            <span class="dk-amount dk-amount--out">{{ euro.format(Number(data.amount)) }}</span>
          </template>
        </PColumn>
        <PColumn v-if="session.isOperator" header="" style="width: 12rem" :pt="{ headerContent: { class: 'justify-end' } }">
          <template #body="{ data }">
            <div class="flex justify-end">
              <PButton
                :label="data.reimbursement_status === 'rimborsato' ? 'Segna da rimborsare' : 'Segna rimborsato'"
                :icon="data.reimbursement_status === 'rimborsato' ? 'pi pi-undo' : 'pi pi-check'"
                :severity="data.reimbursement_status === 'rimborsato' ? 'secondary' : 'success'"
                size="small"
                :outlined="data.reimbursement_status === 'rimborsato'"
                :loading="updating === data.id"
                @click="toggle(data)"
              />
            </div>
          </template>
        </PColumn>
      </PDataTable>
    </div>
    </template>
  </div>
</template>
