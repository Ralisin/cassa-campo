<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import StatusTag from '@/desktop/components/StatusTag.vue'

const props = defineProps({
  movements: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  compact: { type: Boolean, default: false },
  showActions: { type: Boolean, default: false },
  emptyText: { type: String, default: 'Nessun movimento da mostrare' },
})

// While loading the first page, feed the table placeholder rows so the header,
// column widths and row rhythm stay identical to the loaded state.
const showSkeleton = computed(() => props.loading && !props.movements.length)
const rows = computed(() =>
  showSkeleton.value
    ? Array.from({ length: props.compact ? 5 : 8 }, (_, i) => ({ id: `skel-${i}`, __skel: true }))
    : props.movements,
)

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
  if (event.data?.__skel) return
  openDetail(event.data)
}
</script>

<template>
  <PDataTable
    :value="rows"
    data-key="id"
    row-hover
    class="dk-table"
    :class="{ 'dk-table--loading': showSkeleton }"
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
        <Skel v-if="data.__skel" w="3.4rem" h="0.8rem" />
        <span v-else class="dk-table__date">{{ formatDate(data.operation_date) }}</span>
      </template>
    </PColumn>

    <PColumn field="supplier" header="Fornitore">
      <template #body="{ data }">
        <div v-if="data.__skel" class="dk-mv">
          <Skel circle w="2.1rem" h="2.1rem" />
          <div class="min-w-0" style="flex: 1">
            <Skel w="55%" h="0.85rem" />
            <Skel w="35%" h="0.65rem" class="mt-1.5" />
          </div>
        </div>
        <div v-else class="dk-mv">
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
        <Skel v-if="data.__skel" w="4rem" h="1.2rem" r="0.5rem" />
        <span v-else-if="data.category" class="dk-chip">{{ data.category }}</span>
        <span v-else class="dk-muted">—</span>
      </template>
    </PColumn>

    <PColumn v-if="!compact" field="unit" header="Unità" style="width: 6rem">
      <template #body="{ data }">
        <Skel v-if="data.__skel" w="2.5rem" h="1.2rem" r="0.5rem" />
        <span v-else class="dk-chip dk-chip--ghost">{{ data.unit }}</span>
      </template>
    </PColumn>

    <PColumn field="payment_method" header="Metodo" style="width: 7rem">
      <template #body="{ data }">
        <Skel v-if="data.__skel" w="4.5rem" h="0.8rem" />
        <span v-else class="dk-method">
          <i :class="data.payment_method === 'carta' ? 'pi pi-credit-card' : 'pi pi-wallet'" />
          <span class="capitalize">{{ data.payment_method }}</span>
        </span>
      </template>
    </PColumn>

    <PColumn v-if="!compact" field="creator_name" header="Inserito da">
      <template #body="{ data }">
        <Skel v-if="data.__skel" w="5rem" h="0.8rem" />
        <span v-else class="dk-table__creator"><i class="pi pi-user" />{{ data.creator_name }}</span>
      </template>
    </PColumn>

    <PColumn field="reimbursement_status" header="Stato" style="width: 9rem">
      <template #body="{ data }">
        <Skel v-if="data.__skel" w="5.5rem" h="1.4rem" r="0.5rem" />
        <StatusTag v-else :status="data.reimbursement_status" />
      </template>
    </PColumn>

    <PColumn field="amount" header="Importo" style="width: 8rem" :pt="{ headerContent: { class: 'justify-end' } }">
      <template #body="{ data }">
        <div v-if="data.__skel" class="flex justify-end"><Skel w="4.5rem" h="0.9rem" /></div>
        <span v-else class="dk-amount" :class="data.type === 'uscita' ? 'dk-amount--out' : 'dk-amount--in'">
          {{ data.type === 'uscita' ? '−' : '+' }}{{ euro.format(Number(data.amount)) }}
        </span>
      </template>
    </PColumn>

    <PColumn v-if="showActions" header="" style="width: 5.5rem" :pt="{ headerContent: { class: 'justify-end' } }">
      <template #body="{ data }">
        <div v-if="data.__skel" class="dk-table__actions"><Skel circle w="1.6rem" h="1.6rem" /><Skel circle w="1.6rem" h="1.6rem" /></div>
        <div v-else class="dk-table__actions">
          <PButton icon="pi pi-pencil" text rounded size="small" aria-label="Modifica" @click="openEdit($event, data)" />
          <PButton icon="pi pi-arrow-right" text rounded size="small" aria-label="Dettaglio" @click.stop="openDetail(data)" />
        </div>
      </template>
    </PColumn>
  </PDataTable>
</template>
