<script setup>
import { computed, onMounted, ref } from 'vue'
import { useConfirm } from 'primevue/useconfirm'
import { useRoute, useRouter } from 'vue-router'

import { api, downloadReceipt } from '@/api'
import StatusTag from '@/desktop/components/StatusTag.vue'
import PageHeader from '@/desktop/components/PageHeader.vue'
import { useSessionStore } from '@/stores/session'

const route = useRoute()
const router = useRouter()
const session = useSessionStore()
const confirm = useConfirm()
const movement = ref(null)
const receiptBusy = ref('')
const canEdit = computed(() => session.isOperator || movement.value?.created_by === session.user?.id)
const euro = new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' })
const dateFormatter = new Intl.DateTimeFormat('it-IT', { dateStyle: 'long' })
const rows = computed(() => {
  const m = movement.value
  if (!m) return []
  return [
    ['pi pi-calendar', 'Data operazione', dateFormatter.format(new Date(`${m.operation_date}T00:00:00`))],
    ['pi pi-credit-card', 'Metodo', m.payment_method],
    ['pi pi-users', 'Unità', m.unit],
    ['pi pi-book', 'Bilancio', m.balance_type],
    ['pi pi-tag', 'Categoria', m.category || '—'],
    ['pi pi-building', 'Fornitore', m.supplier],
    ['pi pi-file-edit', 'Note', m.notes || '—'],
    ['pi pi-user', 'Inserito da', m.creator_name],
  ]
})

onMounted(async () => (movement.value = await api.get(`/movements/${route.params.id}`)))

function confirmRemove(event) {
  confirm.require({
    target: event.currentTarget,
    message: 'Eliminare definitivamente questo movimento?',
    icon: 'pi pi-exclamation-triangle',
    header: 'Conferma eliminazione',
    rejectlabel: 'Annulla',
    acceptLabel: 'Elimina',
    acceptClass: 'p-button-danger',
    accept: remove,
  })
}

async function remove() {
  await api.delete(`/movements/${route.params.id}`)
  router.push('/movimenti')
}

async function toggleReimbursed() {
  const result = await api.put(`/reimbursements/${movement.value.id}`, {
    reimbursed: movement.value.reimbursement_status !== 'rimborsato',
  })
  movement.value = result.movements.find((item) => item.id === movement.value.id)
}

async function download(receipt) {
  receiptBusy.value = receipt.id
  try {
    await downloadReceipt(movement.value.id, receipt)
  } finally {
    receiptBusy.value = ''
  }
}

async function deleteReceipt(receipt) {
  receiptBusy.value = receipt.id
  try {
    await api.delete(`/movements/${movement.value.id}/receipts/${receipt.id}`)
    movement.value.receipts = movement.value.receipts.filter((item) => item.id !== receipt.id)
  } finally {
    receiptBusy.value = ''
  }
}

function formatBytes(bytes) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}
</script>

<template>
  <div v-if="movement">
    <PageHeader title="Dettaglio movimento" :subtitle="movement.supplier">
      <template #actions>
        <PButton label="Movimenti" icon="pi pi-arrow-left" text @click="router.push('/movimenti')" />
        <RouterLink v-if="canEdit" :to="`/movimenti/${movement.id}/modifica`">
          <PButton label="Modifica" icon="pi pi-pencil" outlined />
        </RouterLink>
        <PButton v-if="canEdit" label="Elimina" icon="pi pi-trash" severity="danger" outlined @click="confirmRemove" />
      </template>
    </PageHeader>

    <div class="dk-form-grid">
      <div class="dk-card">
        <div class="flex items-center gap-4 border-b border-slate-100 pb-5">
          <span class="dk-mv__avatar" :class="movement.type === 'uscita' ? 'dk-mv__avatar--out' : 'dk-mv__avatar--in'" style="width: 3.4rem; height: 3.4rem; font-size: 1.2rem; border-radius: 0.9rem">
            <i :class="movement.payment_method === 'carta' ? 'pi pi-credit-card' : 'pi pi-wallet'" />
          </span>
          <div class="min-w-0 flex-1">
            <h2 class="truncate text-xl font-black">{{ movement.supplier }}</h2>
            <div class="mt-1 flex items-center gap-2">
              <PTag :value="movement.type" :severity="movement.type === 'uscita' ? 'danger' : 'success'" class="capitalize" />
              <StatusTag :status="movement.reimbursement_status" />
            </div>
          </div>
          <p class="text-2xl font-black" :class="movement.type === 'uscita' ? 'text-red-600' : 'text-emerald-700'">
            {{ movement.type === 'uscita' ? '−' : '+' }}{{ euro.format(Number(movement.amount)) }}
          </p>
        </div>

        <div class="dk-define mt-2">
          <div v-for="[icon, label, value] in rows" :key="label" class="dk-define__row">
            <i :class="icon" />
            <span class="dk-define__label">{{ label }}</span>
            <span class="dk-define__value capitalize">{{ value }}</span>
          </div>
        </div>
      </div>

      <div class="dk-stack">
        <div v-if="session.isOperator && movement.needs_reimbursement" class="dk-card">
          <h3 class="dk-card__title mb-3"><i class="pi pi-replay dk-card__title-icon" /> Rimborso</h3>
          <PButton
            :label="movement.reimbursement_status === 'rimborsato' ? 'Segna da rimborsare' : 'Segna come rimborsato'"
            :icon="movement.reimbursement_status === 'rimborsato' ? 'pi pi-undo' : 'pi pi-check-circle'"
            :severity="movement.reimbursement_status === 'rimborsato' ? 'secondary' : 'success'"
            fluid
            @click="toggleReimbursed"
          />
        </div>

        <div class="dk-card">
          <h3 class="dk-card__title mb-3">
            <i class="pi pi-paperclip dk-card__title-icon" /> Scontrini
            <span class="ml-1 text-sm font-semibold text-slate-400">({{ movement.receipts.length }})</span>
          </h3>
          <div v-if="movement.receipts.length" class="space-y-2">
            <div v-for="receipt in movement.receipts" :key="receipt.id" class="dk-receipt">
              <i :class="receipt.content_type === 'application/pdf' ? 'pi pi-file-pdf' : 'pi pi-image'" class="text-slate-500" />
              <span class="min-w-0 flex-1">
                <strong class="block truncate text-xs text-slate-800">{{ receipt.filename }}</strong>
                <span class="block text-[11px] font-semibold text-slate-500">{{ formatBytes(receipt.size_bytes) }}</span>
              </span>
              <PButton icon="pi pi-download" text rounded severity="secondary" aria-label="Scarica" class="!h-8 !w-8" :loading="receiptBusy === receipt.id" @click="download(receipt)" />
              <PButton v-if="canEdit" icon="pi pi-trash" text rounded severity="danger" aria-label="Elimina" class="!h-8 !w-8" :disabled="receiptBusy === receipt.id" @click="deleteReceipt(receipt)" />
            </div>
          </div>
          <p v-else class="rounded-lg bg-slate-50 px-3 py-3 text-center text-xs font-semibold text-slate-500">Nessuno scontrino caricato.</p>
        </div>
      </div>
    </div>
  </div>
</template>
