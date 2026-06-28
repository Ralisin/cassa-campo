<script setup>
import { useRouter } from 'vue-router'

import StatusTag from '@/desktop/components/StatusTag.vue'

const props = defineProps({
  movements: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  compact: { type: Boolean, default: false },
  showActions: { type: Boolean, default: false },
  emptyText: { type: String, default: 'Nessun movimento da mostrare' },
})

const router = useRouter()
const euro = new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' })
const dateFormatter = new Intl.DateTimeFormat('it-IT', { day: '2-digit', month: 'short', year: '2-digit' })

function formatDate(value) {
  return dateFormatter.format(new Date(`${value}T00:00:00`)).replace(/\./g, '')
}

function openDetail(movement) {
  router.push(`/movimenti/${movement.id}`)
}

function openEdit(event, movement) {
  event.stopPropagation()
  router.push(`/movimenti/${movement.id}/modifica`)
}

function onRowClick(event) {
  openDetail(event.data)
}
</script>

<template>
  <PDataTable
    :value="movements"
    data-key="id"
    :loading="loading"
    row-hover
    class="dk-table"
    :pt="{ bodyRow: { class: 'dk-table__row' } }"
    @row-click="onRowClick"
  >
    <template #empty>
      <div class="dk-table__empty">
        <i class="pi pi-inbox" />
        <span>{{ emptyText }}</span>
      </div>
    </template>

    <PColumn field="operation_date" header="Data" style="width: 6.5rem">
      <template #body="{ data }">
        <span class="dk-table__date">{{ formatDate(data.operation_date) }}</span>
      </template>
    </PColumn>

    <PColumn field="supplier" header="Fornitore">
      <template #body="{ data }">
        <div class="dk-mv">
          <span class="dk-mv__avatar" :class="data.type === 'uscita' ? 'dk-mv__avatar--out' : 'dk-mv__avatar--in'">
            <i :class="data.payment_method === 'carta' ? 'pi pi-credit-card' : 'pi pi-wallet'" />
          </span>
          <div class="min-w-0">
            <span class="dk-mv__name">{{ data.supplier }}</span>
            <span v-if="data.notes" class="dk-mv__notes">{{ data.notes }}</span>
          </div>
        </div>
      </template>
    </PColumn>

    <PColumn v-if="!compact" field="category" header="Categoria">
      <template #body="{ data }">
        <span v-if="data.category" class="dk-chip">{{ data.category }}</span>
        <span v-else class="dk-muted">—</span>
      </template>
    </PColumn>

    <PColumn v-if="!compact" field="unit" header="Unità" style="width: 6rem">
      <template #body="{ data }"><span class="dk-chip dk-chip--ghost">{{ data.unit }}</span></template>
    </PColumn>

    <PColumn field="payment_method" header="Metodo" style="width: 7rem">
      <template #body="{ data }">
        <span class="dk-method">
          <i :class="data.payment_method === 'carta' ? 'pi pi-credit-card' : 'pi pi-wallet'" />
          <span class="capitalize">{{ data.payment_method }}</span>
        </span>
      </template>
    </PColumn>

    <PColumn v-if="!compact" field="creator_name" header="Inserito da">
      <template #body="{ data }">
        <span class="dk-table__creator"><i class="pi pi-user" />{{ data.creator_name }}</span>
      </template>
    </PColumn>

    <PColumn field="reimbursement_status" header="Stato" style="width: 9rem">
      <template #body="{ data }"><StatusTag :status="data.reimbursement_status" /></template>
    </PColumn>

    <PColumn field="amount" header="Importo" style="width: 8rem" :pt="{ headerContent: { class: 'justify-end' } }">
      <template #body="{ data }">
        <span class="dk-amount" :class="data.type === 'uscita' ? 'dk-amount--out' : 'dk-amount--in'">
          {{ data.type === 'uscita' ? '−' : '+' }}{{ euro.format(Number(data.amount)) }}
        </span>
      </template>
    </PColumn>

    <PColumn v-if="showActions" header="" style="width: 5.5rem" :pt="{ headerContent: { class: 'justify-end' } }">
      <template #body="{ data }">
        <div class="dk-table__actions">
          <PButton icon="pi pi-pencil" text rounded size="small" aria-label="Modifica" @click="openEdit($event, data)" />
          <PButton icon="pi pi-arrow-right" text rounded size="small" aria-label="Dettaglio" @click.stop="openDetail(data)" />
        </div>
      </template>
    </PColumn>
  </PDataTable>
</template>
