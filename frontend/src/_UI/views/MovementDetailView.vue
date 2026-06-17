<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, downloadReceipt } from '@/api'
import { useSessionStore } from '@/stores/session'

const route = useRoute()
const router = useRouter()
const session = useSessionStore()
const movement = ref(null)
const receiptBusy = ref('')
const canEdit = computed(
  () => session.isOperator || movement.value?.created_by === session.user?.id,
)
const euro = new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' })
const rows = [
  ['pi pi-calendar', 'Data operazione', 'operation_date'],
  ['pi pi-credit-card', 'Metodo', 'payment_method'],
  ['pi pi-users', 'Unità', 'unit'],
  ['pi pi-book', 'Bilancio', 'balance_type'],
  ['pi pi-tag', 'Categoria', 'category'],
  ['pi pi-building', 'Fornitore', 'supplier'],
  ['pi pi-file-edit', 'Note', 'notes'],
]
onMounted(async () => (movement.value = await api.get(`/movements/${route.params.id}`)))
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
  <main v-if="movement">
    <PCard>
      <template #content>
        <section class="grid place-items-center border-b border-slate-200 px-5 pb-8 pt-4 text-center">
          <PAvatar :icon="movement.payment_method === 'carta' ? 'pi pi-credit-card' : 'pi pi-wallet'" size="xlarge" shape="circle" class="!bg-emerald-50 !text-forest" />
          <h2 class="mt-4 text-xl font-black">{{ movement.supplier }}</h2>
          <PTag :value="movement.type" :severity="movement.type === 'uscita' ? 'danger' : 'success'" class="mt-2 capitalize" />
          <p class="mt-4 text-3xl font-black" :class="movement.type === 'uscita' ? 'text-red-600' : 'text-emerald-700'">{{ movement.type === 'uscita' ? '−' : '+' }}{{ euro.format(Number(movement.amount)) }}</p>
          <PTag v-if="movement.reimbursement_status === 'da_rimborsare'" value="Da rimborsare" severity="warn" class="mt-2" />
          <PTag v-else-if="movement.reimbursement_status === 'rimborsato'" value="Rimborsato" severity="success" class="mt-2" />
        </section>
        <section v-if="session.isOperator && movement.needs_reimbursement" class="movement-detail-reimbursement border-t border-slate-200 pt-4">
          <PButton
            :label="movement.reimbursement_status === 'rimborsato' ? 'Segna da rimborsare' : 'Segna come rimborsato'"
            :icon="movement.reimbursement_status === 'rimborsato' ? 'pi pi-undo' : 'pi pi-check-circle'"
            :severity="movement.reimbursement_status === 'rimborsato' ? 'secondary' : 'success'"
            class="movement-detail-reimbursement__button"
            :class="{ 'movement-detail-reimbursement__button--completed': movement.reimbursement_status === 'rimborsato' }"
            fluid
            @click="toggleReimbursed"
          />
        </section>
        <section class="divide-y divide-slate-100">
          <div v-for="[icon, label, key] in rows" :key="key" class="flex items-center gap-3 py-4 text-sm">
            <i :class="icon" class="text-slate-500" /><span class="flex-1 font-semibold text-slate-600">{{ label }}</span><span class="text-right font-medium">{{ movement[key] || '—' }}</span>
          </div>
        </section>
        <section class="movement-detail-receipts border-t border-slate-200 pt-4">
          <div class="mb-3 flex items-center gap-3">
            <PAvatar icon="pi pi-paperclip" shape="circle" class="!bg-emerald-50 !text-forest" />
            <div class="min-w-0 flex-1">
              <h3 class="text-sm font-black text-forest">Scontrini</h3>
              <p class="text-xs font-medium text-slate-500">{{ movement.receipts.length || 'Nessun' }} {{ movement.receipts.length === 1 ? 'allegato' : 'allegati' }}</p>
            </div>
          </div>
          <div v-if="movement.receipts.length" class="space-y-2">
            <div v-for="receipt in movement.receipts" :key="receipt.id" class="receipt-upload-item">
              <i :class="receipt.content_type === 'application/pdf' ? 'pi pi-file-pdf' : 'pi pi-image'" class="text-slate-500" />
              <span class="min-w-0 flex-1">
                <strong class="block truncate text-xs text-slate-800">{{ receipt.filename }}</strong>
                <span class="block text-[11px] font-semibold text-slate-500">{{ formatBytes(receipt.size_bytes) }}</span>
              </span>
              <PButton icon="pi pi-download" text rounded severity="secondary" aria-label="Scarica scontrino" class="!h-8 !w-8" :loading="receiptBusy === receipt.id" @click="download(receipt)" />
              <PButton v-if="canEdit" icon="pi pi-trash" text rounded severity="danger" aria-label="Elimina scontrino" class="!h-8 !w-8" :disabled="receiptBusy === receipt.id" @click="deleteReceipt(receipt)" />
            </div>
          </div>
          <p v-else class="rounded-lg bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-500">Nessuno scontrino caricato.</p>
        </section>
        <section v-if="canEdit" class="movement-detail-actions grid grid-cols-2 gap-3 border-t border-slate-200 pt-4">
          <RouterLink class="movement-detail-actions__link" :to="`/movimenti/${movement.id}/modifica`">
            <PButton label="Modifica" icon="pi pi-pencil" class="movement-detail-action movement-detail-action--edit" fluid />
          </RouterLink>
          <PButton label="Elimina" icon="pi pi-trash" class="movement-detail-action movement-detail-action--delete" fluid @click="remove" />
        </section>
      </template>
    </PCard>
  </main>
</template>
