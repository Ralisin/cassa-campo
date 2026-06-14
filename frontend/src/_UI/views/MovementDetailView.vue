<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api'
import { useSessionStore } from '@/stores/session'

const route = useRoute()
const router = useRouter()
const session = useSessionStore()
const movement = ref(null)
const canEdit = computed(
  () => session.isAdmin || movement.value?.created_by === session.user?.id,
)
const euro = new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' })
const rows = [
  ['pi pi-calendar', 'Data operazione', 'operation_date'],
  ['pi pi-credit-card', 'Metodo', 'payment_method'],
  ['pi pi-users', 'Unità', 'unit'],
  ['pi pi-book', 'Bilancio', 'balance_type'],
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
        <section v-if="session.isAdmin && movement.needs_reimbursement" class="movement-detail-reimbursement border-t border-slate-200 pt-4">
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
