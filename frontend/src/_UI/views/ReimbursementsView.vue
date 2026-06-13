<script setup>
import { computed, onMounted, ref } from 'vue'

import { api } from '@/api'
import MovementCard from '@/_UI/components/MovementCard.vue'
import { useSessionStore } from '@/stores/session'

const session = useSessionStore()
const summary = ref(null)
const statusFilter = ref('da_rimborsare')
const creatorFilter = ref('tutti')
const updating = ref(null)
const euro = new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' })
const statuses = [
  { label: 'Da rimborsare', value: 'da_rimborsare', icon: 'pi pi-clock' },
  { label: 'Rimborsati', value: 'rimborsato', icon: 'pi pi-check-circle' },
  { label: 'Tutti', value: 'tutti', icon: 'pi pi-list' },
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

function formatDateTime(value) {
  return new Intl.DateTimeFormat('it-IT', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

onMounted(load)
</script>

<template>
  <main v-if="summary" class="space-y-4">
    <section class="grid grid-cols-2 gap-3">
      <PCard class="reimbursement-summary-card reimbursement-summary-card--pending">
        <template #content>
          <PAvatar icon="pi pi-clock" shape="circle" class="!bg-amber-100 !text-amber-700" />
          <p class="mt-3 text-[11px] font-black uppercase tracking-wider text-slate-500">{{ session.isAdmin ? 'Da restituire' : 'Ti devono restituire' }}</p>
          <p class="mt-1 text-xl font-black text-amber-700">{{ euro.format(Number(summary.pending_amount)) }}</p>
          <p class="mt-1 text-xs text-slate-500">{{ summary.pending_count }} movimenti</p>
        </template>
      </PCard>
      <PCard class="reimbursement-summary-card">
        <template #content>
          <PAvatar icon="pi pi-check-circle" shape="circle" class="!bg-emerald-50 !text-emerald-700" />
          <p class="mt-3 text-[11px] font-black uppercase tracking-wider text-slate-500">Già rimborsati</p>
          <p class="mt-1 text-xl font-black text-emerald-700">{{ euro.format(Number(summary.reimbursed_amount)) }}</p>
          <p class="mt-1 text-xs text-slate-500">{{ summary.reimbursed_count }} movimenti</p>
        </template>
      </PCard>
    </section>

    <PCard class="reimbursement-filters">
      <template #content>
        <div class="movement-filter-segments reimbursement-filter-segments">
          <PButton v-for="item in statuses" :key="item.value" :label="item.label" :icon="item.icon" size="small" class="movement-filter-segment reimbursement-filter-segment" :class="{ 'movement-filter-segment--active': statusFilter === item.value }" @click="statusFilter = item.value" />
        </div>
        <PSelect v-if="session.isAdmin" v-model="creatorFilter" :options="creators" option-label="label" option-value="value" class="mt-3" fluid />
      </template>
    </PCard>

    <section v-if="filtered.length" class="space-y-3">
      <article v-for="movement in filtered" :key="movement.id" class="reimbursement-list-item">
        <MovementCard :movement="movement" />
        <p v-if="movement.reimbursed_at" class="reimbursement-list-item__meta text-xs text-slate-500">
          Rimborsato il {{ formatDateTime(movement.reimbursed_at) }}
          <span v-if="movement.reimbursed_by_name"> da {{ movement.reimbursed_by_name }}</span>
        </p>
        <PButton
          v-if="session.isAdmin"
          :label="movement.reimbursement_status === 'rimborsato' ? 'Segna da rimborsare' : 'Segna come rimborsato'"
          :icon="movement.reimbursement_status === 'rimborsato' ? 'pi pi-undo' : 'pi pi-check-circle'"
          :severity="movement.reimbursement_status === 'rimborsato' ? 'secondary' : 'success'"
          class="reimbursement-list-action"
          :class="{ 'reimbursement-list-action--completed': movement.reimbursement_status === 'rimborsato' }"
          fluid
          :loading="updating === movement.id"
          @click="toggle(movement)"
        />
      </article>
    </section>

    <PCard v-else class="movements-empty">
      <template #content>
        <div class="grid place-items-center py-8 text-center">
          <PAvatar icon="pi pi-check-circle" size="xlarge" shape="circle" class="!bg-emerald-50 !text-emerald-700" />
          <h2 class="mt-4 text-base font-black">Nessun rimborso in questa sezione</h2>
          <p class="mt-1 text-sm text-slate-500">Prova a cambiare il filtro selezionato.</p>
        </div>
      </template>
    </PCard>
  </main>
</template>
