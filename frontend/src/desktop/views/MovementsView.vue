<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { api } from '@/api'
import { usePolling } from '@/composables/usePolling'
import MovementsTable from '@/desktop/components/MovementsTable.vue'
import PageHeader from '@/desktop/components/PageHeader.vue'

const route = useRoute()
const movements = ref([])
const creatorOptions = ref([])
const nextCursor = ref(null)
const total = ref(0)
const loading = ref(false)
const error = ref('')
const trashOpen = ref(false)
const trashLoading = ref(false)
const deletedMovements = ref([])

const query = ref(typeof route.query.q === 'string' ? route.query.q : '')
const type = ref('tutti')
const method = ref('tutti')
const creator = ref('tutti')
const reimbursement = ref('tutti')

const typeOptions = [
  { label: 'Tutti i tipi', value: 'tutti' },
  { label: 'Entrate', value: 'entrata' },
  { label: 'Uscite', value: 'uscita' },
]
const methodOptions = [
  { label: 'Tutti i metodi', value: 'tutti' },
  { label: 'Contanti', value: 'contanti' },
  { label: 'Carta', value: 'carta' },
]
const reimbursementOptions = [
  { label: 'Tutti i rimborsi', value: 'tutti' },
  { label: 'Da rimborsare', value: 'da_rimborsare' },
  { label: 'Rimborsati', value: 'rimborsato' },
  { label: 'Senza rimborso', value: 'nessuno' },
]
const creators = computed(() => [
  { label: 'Tutti gli utenti', value: 'tutti' },
  ...creatorOptions.value.map((item) => ({ label: item.name, value: item.id })),
])
const euro = new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' })
const activeFilters = computed(() => [
  query.value.trim(),
  type.value !== 'tutti',
  method.value !== 'tutti',
  creator.value !== 'tutti',
  reimbursement.value !== 'tutti',
].filter(Boolean).length)

let requestVersion = 0
let searchTimer

function movementsPath(cursor = null) {
  const params = new URLSearchParams()
  if (cursor) params.set('cursor', cursor)
  if (query.value.trim()) params.set('query', query.value.trim())
  if (type.value !== 'tutti') params.set('movement_type', type.value)
  if (method.value !== 'tutti') params.set('payment_method', method.value)
  if (creator.value !== 'tutti') params.set('creator', creator.value)
  if (reimbursement.value !== 'tutti') params.set('reimbursement', reimbursement.value)
  return `/movements?${params}`
}

async function loadFirstPage() {
  const version = ++requestVersion
  loading.value = true
  error.value = ''
  try {
    const page = await api.get(movementsPath())
    if (version !== requestVersion) return
    movements.value = page.items
    creatorOptions.value = page.creators
    nextCursor.value = page.next_cursor
    total.value = page.total
  } catch (cause) {
    if (version !== requestVersion) return
    error.value = cause instanceof Error ? cause.message : 'Caricamento movimenti non riuscito'
  } finally {
    if (version === requestVersion) loading.value = false
  }
}

async function loadMore() {
  if (!nextCursor.value || loading.value) return
  const version = requestVersion
  loading.value = true
  error.value = ''
  try {
    const page = await api.get(movementsPath(nextCursor.value))
    if (version !== requestVersion) return
    movements.value = [...movements.value, ...page.items]
    nextCursor.value = page.next_cursor
    total.value = page.total
  } catch (cause) {
    if (version !== requestVersion) return
    error.value = cause instanceof Error ? cause.message : 'Caricamento altri movimenti non riuscito'
  } finally {
    if (version === requestVersion) loading.value = false
  }
}

async function refreshFirstPage() {
  const version = requestVersion
  const page = await api.get(movementsPath())
  if (version !== requestVersion) return
  const firstPageIds = new Set(page.items.map((movement) => movement.id))
  movements.value = [
    ...page.items,
    ...movements.value.filter((movement) => !firstPageIds.has(movement.id)),
  ]
  creatorOptions.value = page.creators
  total.value = page.total
}

function resetFilters() {
  query.value = ''
  type.value = 'tutti'
  method.value = 'tutti'
  creator.value = 'tutti'
  reimbursement.value = 'tutti'
}

async function openTrash() {
  trashOpen.value = true
  trashLoading.value = true
  try {
    deletedMovements.value = await api.get('/movements/deleted')
  } finally {
    trashLoading.value = false
  }
}

async function restoreMovement(movement) {
  await api.put(`/movements/${movement.id}/restore`, {})
  deletedMovements.value = deletedMovements.value.filter((item) => item.id !== movement.id)
  await loadFirstPage()
}

watch([type, method, creator, reimbursement], loadFirstPage)
watch(query, () => {
  window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(loadFirstPage, 300)
})
// Keep in sync with a search submitted from the topbar.
watch(() => route.query.q, (value) => {
  const next = typeof value === 'string' ? value : ''
  if (next !== query.value) query.value = next
})

onMounted(loadFirstPage)
onUnmounted(() => window.clearTimeout(searchTimer))
usePolling(refreshFirstPage)
</script>

<template>
  <div>
    <PageHeader title="Movimenti" :subtitle="`${total} ${total === 1 ? 'movimento registrato' : 'movimenti registrati'}`" />

    <div class="dk-card">
      <div class="dk-toolbar">
        <PIconField class="dk-toolbar__search">
          <PInputIcon class="pi pi-search" />
          <PInputText v-model="query" placeholder="Cerca per fornitore o note…" fluid />
        </PIconField>
        <PSelect v-model="type" :options="typeOptions" option-label="label" option-value="value" />
        <PSelect v-model="method" :options="methodOptions" option-label="label" option-value="value" />
        <PSelect v-model="creator" :options="creators" option-label="label" option-value="value" filter />
        <PSelect v-model="reimbursement" :options="reimbursementOptions" option-label="label" option-value="value" />
        <PButton
          v-if="activeFilters"
          label="Azzera"
          icon="pi pi-filter-slash"
          text
          class="dk-toolbar__spacer"
          @click="resetFilters"
        />
        <PButton label="Cestino" icon="pi pi-trash" text @click="openTrash" />
      </div>

      <PMessage v-if="error" severity="error" size="small" class="mb-3">
        {{ error }}
        <PButton label="Riprova" icon="pi pi-refresh" size="small" text class="movement-inline-retry" @click="loadFirstPage" />
      </PMessage>

      <MovementsTable
        v-if="!error"
        :movements="movements"
        :loading="loading && !movements.length"
        show-actions
        :empty-text="activeFilters ? 'Nessun movimento corrisponde ai filtri' : 'Nessun movimento registrato'"
      />

      <div class="mt-4 flex items-center justify-center">
        <PButton
          v-if="nextCursor"
          label="Carica altri"
          icon="pi pi-chevron-down"
          outlined
          :loading="loading"
          @click="loadMore"
        />
        <span v-else-if="movements.length" class="text-sm text-slate-400">
          {{ movements.length }} di {{ total }} movimenti
        </span>
      </div>
    </div>

    <PDialog v-model:visible="trashOpen" modal header="Cestino movimenti" class="summary-dialog w-[34rem]">
      <div v-if="trashLoading" class="dk-skel-rows">
        <div v-for="n in 3" :key="n" class="dk-skel-row"><Skel w="45%" h="0.8rem" /><Skel w="6rem" h="2rem" /></div>
      </div>
      <p v-else-if="!deletedMovements.length" class="py-6 text-center text-sm font-semibold text-slate-500">Nessun movimento nel cestino.</p>
      <div v-else class="space-y-2">
        <article v-for="movement in deletedMovements" :key="movement.id" class="trash-item">
          <span class="min-w-0 flex-1">
            <strong>{{ movement.supplier }}</strong>
            <small>{{ euro.format(Number(movement.amount)) }} · {{ movement.operation_date }}</small>
          </span>
          <PButton label="Ripristina" icon="pi pi-undo" size="small" @click="restoreMovement(movement)" />
        </article>
      </div>
    </PDialog>
  </div>
</template>
