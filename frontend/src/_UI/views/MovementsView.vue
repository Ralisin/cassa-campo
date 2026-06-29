<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api'
import { usePolling } from '@/composables/usePolling'
import MovementCard from '@/_UI/components/MovementCard.vue'
import MovementCardSkeleton from '@/_UI/components/MovementCardSkeleton.vue'

const movements = ref([])
const creatorOptions = ref([])
const nextCursor = ref(null)
const total = ref(0)
const loading = ref(false)
const error = ref('')
const trashOpen = ref(false)
const trashLoading = ref(false)
const deletedMovements = ref([])
const loadMoreSentinel = ref(null)
const router = useRouter()
const query = ref('')
const type = ref('tutti')
const method = ref('tutti')
const creator = ref('tutti')
const reimbursement = ref('tutti')
const collapsedDates = ref(new Set())
const filtersCollapsed = ref(true)
const filters = [
  { label: 'Tutti', value: 'tutti', icon: 'pi pi-list' },
  { label: 'Entrate', value: 'entrata', icon: 'pi pi-arrow-down-left' },
  { label: 'Uscite', value: 'uscita', icon: 'pi pi-arrow-up-right' },
]
const methods = [
  { label: 'Tutti', value: 'tutti', icon: 'pi pi-th-large' },
  { label: 'Contanti', value: 'contanti', icon: 'pi pi-wallet' },
  { label: 'Carta', value: 'carta', icon: 'pi pi-credit-card' },
]
const reimbursementFilters = [
  { label: 'Tutti', value: 'tutti' },
  { label: 'Da rimborsare', value: 'da_rimborsare' },
  { label: 'Rimborsati', value: 'rimborsato' },
  { label: 'Senza rimborso', value: 'nessuno' },
]
const dateFormatter = new Intl.DateTimeFormat('it-IT', {
  weekday: 'short',
  day: 'numeric',
  month: 'short',
})
const euro = new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' })
const creators = computed(() => [
  { label: 'Tutti gli utenti', value: 'tutti' },
  ...creatorOptions.value.map((item) => ({ label: item.name, value: item.id })),
])
const activeFilters = computed(() => [
  query.value.trim(),
  type.value !== 'tutti',
  method.value !== 'tutti',
  creator.value !== 'tutti',
  reimbursement.value !== 'tutti',
].filter(Boolean).length)
const grouped = computed(() => movements.value.reduce((groups, movement) => {
  groups[movement.operation_date] ??= []
  groups[movement.operation_date].push(movement)
  return groups
}, {}))

let requestVersion = 0
let searchTimer
let infiniteScrollObserver

async function rearmInfiniteScroll() {
  await nextTick()
  if (!infiniteScrollObserver || !loadMoreSentinel.value) return
  infiniteScrollObserver.unobserve(loadMoreSentinel.value)
  infiniteScrollObserver.observe(loadMoreSentinel.value)
}

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
    if (version === requestVersion) {
      loading.value = false
      rearmInfiniteScroll()
    }
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
    if (version === requestVersion) {
      loading.value = false
      rearmInfiniteScroll()
    }
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

onMounted(() => {
  infiniteScrollObserver = new IntersectionObserver(
    ([entry]) => {
      if (entry.isIntersecting) loadMore()
    },
    { rootMargin: '300px 0px' },
  )
  infiniteScrollObserver.observe(loadMoreSentinel.value)
  loadFirstPage()
})
usePolling(refreshFirstPage)

watch([type, method, creator, reimbursement], loadFirstPage)
watch(query, () => {
  window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(loadFirstPage, 300)
})
onUnmounted(() => {
  window.clearTimeout(searchTimer)
  infiniteScrollObserver?.disconnect()
})

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

function toggleDate(date) {
  const next = new Set(collapsedDates.value)
  if (next.has(date)) next.delete(date)
  else next.add(date)
  collapsedDates.value = next
}

function formatDate(date) {
  return dateFormatter.format(new Date(`${date}T00:00:00`)).replace(/\./g, '')
}
</script>

<template>
  <main class="movements-page space-y-4">
    <PCard class="movements-filters">
      <template #content>
        <div class="flex gap-2">
          <PIconField class="min-w-0 flex-1"><PInputIcon class="pi pi-search" /><PInputText v-model="query" placeholder="Cerca movimenti..." fluid /></PIconField>
          <PButton icon="pi pi-plus" rounded aria-label="Nuovo movimento" class="primary-cta !h-11 !min-h-0 !w-11 !min-w-11 !p-0" @click="router.push('/movimenti/nuovo')" />
        </div>

        <button type="button" class="movement-filters-toggle" :aria-expanded="!filtersCollapsed" @click="filtersCollapsed = !filtersCollapsed">
          <span class="movement-filters-toggle__icon"><i class="pi pi-sliders-h" /></span>
          <span class="min-w-0 flex-1 text-left">
            <strong class="block text-xs text-slate-800">Filtri</strong>
            <span class="block text-[11px] font-medium text-slate-500">{{ total }} risultati</span>
          </span>
          <span v-if="activeFilters" class="movement-filters-toggle__count">{{ activeFilters }} attivi</span>
          <span class="movement-filters-toggle__chevron" :class="{ 'movement-filters-toggle__chevron--collapsed': filtersCollapsed }"><i class="pi pi-chevron-up" /></span>
        </button>
        <div v-if="activeFilters" class="movement-filters-clear">
          <span>{{ activeFilters }} {{ activeFilters === 1 ? 'filtro attivo' : 'filtri attivi' }}</span>
          <PButton label="Azzera" icon="pi pi-filter-slash" size="small" text class="movement-filters-clear__button" @click="resetFilters" />
        </div>
        <PButton label="Cestino" icon="pi pi-trash" size="small" text class="movement-filters-clear__button mt-2" @click="openTrash" />

        <Transition name="movement-group">
          <div v-if="!filtersCollapsed" class="movement-group-content">
            <div>
              <div class="mt-3">
                <p class="mb-1.5 text-[11px] font-black uppercase tracking-wider text-slate-400">Tipo</p>
                <div class="movement-filter-segments">
                  <PButton v-for="filter in filters" :key="filter.value" :label="filter.label" :icon="filter.icon" size="small" class="movement-filter-segment" :class="{ 'movement-filter-segment--active': type === filter.value }" @click="type = filter.value" />
                </div>
              </div>

              <div class="mt-3 flex items-center justify-end gap-2 overflow-x-auto">
                <PButton v-for="item in methods" :key="item.value" :label="item.label" :icon="item.icon" size="small" rounded class="movement-method-chip" :class="{ 'movement-method-chip--active': method === item.value }" @click="method = item.value" />
              </div>

              <div class="movement-creator-filter-wrap">
                <PAvatar icon="pi pi-user" shape="circle" class="!bg-emerald-50 !text-forest" />
                <div class="min-w-0 flex-1">
                  <p class="text-[10px] font-black uppercase tracking-wider text-slate-400">Movimenti inseriti da</p>
                  <PSelect v-model="creator" :options="creators" option-label="label" option-value="value" class="movement-creator-filter" fluid>
                    <template #value="{ value }">
                      <span class="font-bold text-slate-800">{{ creators.find((item) => item.value === value)?.label }}</span>
                    </template>
                    <template #option="{ option }">
                      <div class="flex items-center gap-2">
                        <PAvatar :icon="option.value === 'tutti' ? 'pi pi-users' : 'pi pi-user'" shape="circle" class="!h-7 !w-7 !bg-slate-100 !text-slate-600" />
                        <span class="font-semibold">{{ option.label }}</span>
                        <i v-if="creator === option.value" class="pi pi-check ml-auto text-forest" />
                      </div>
                    </template>
                  </PSelect>
                </div>
              </div>
              <div class="mt-3">
                <p class="mb-1.5 text-[11px] font-black uppercase tracking-wider text-slate-400">Rimborso</p>
                <PSelect v-model="reimbursement" :options="reimbursementFilters" option-label="label" option-value="value" fluid />
              </div>
            </div>
          </div>
        </Transition>
      </template>
    </PCard>

    <PMessage v-if="error" severity="error" size="small">
      {{ error }}
      <PButton label="Riprova" icon="pi pi-refresh" size="small" text class="movement-inline-retry" @click="loadFirstPage" />
    </PMessage>

    <div v-if="loading && !movements.length" class="space-y-4" aria-hidden="true">
      <section v-for="group in 2" :key="group">
        <div class="movement-date-toggle" style="cursor: default">
          <Skel w="8rem" h="0.9rem" />
          <span class="movement-date-toggle__line" />
          <Skel circle w="1.65rem" h="1.65rem" />
        </div>
        <div class="space-y-2"><MovementCardSkeleton v-for="n in 3" :key="n" /></div>
      </section>
    </div>

    <section v-for="(items, date) in grouped" :key="date">
      <button
        type="button"
        class="movement-date-toggle"
        :aria-expanded="!collapsedDates.has(date)"
        @click="toggleDate(date)"
      >
        <strong class="capitalize text-slate-700">{{ formatDate(date) }}</strong>
        <span class="movement-date-toggle__count">{{ items.length }} {{ items.length === 1 ? 'movimento' : 'movimenti' }}</span>
        <span class="movement-date-toggle__line" />
        <span class="movement-date-toggle__chevron" :class="{ 'movement-date-toggle__chevron--collapsed': collapsedDates.has(date) }">
          <i class="pi pi-chevron-up" />
        </span>
      </button>
      <Transition name="movement-group">
        <div v-if="!collapsedDates.has(date)" class="movement-group-content">
          <div>
            <PDataView :value="items" class="movement-data-view">
              <template #list="{ items: movementsForDate }">
                <div class="space-y-2">
                  <MovementCard v-for="movement in movementsForDate" :key="movement.id" :movement="movement" />
                </div>
              </template>
            </PDataView>
          </div>
        </div>
      </Transition>
    </section>
    <div ref="loadMoreSentinel" class="flex min-h-12 items-center justify-center py-2" aria-live="polite">
      <i v-if="loading && movements.length" class="pi pi-spin pi-spinner text-xl text-forest" aria-hidden="true" />
      <span v-if="loading && movements.length" class="sr-only">Caricamento altri movimenti</span>
    </div>
    <PCard v-if="!loading && !error && !movements.length" class="movements-empty">
      <template #content>
        <div class="grid place-items-center py-8 text-center">
          <PAvatar icon="pi pi-receipt" size="xlarge" shape="circle" class="!bg-emerald-50 !text-forest" />
          <h2 class="mt-4 text-base font-black text-slate-800">{{ activeFilters ? 'Nessun risultato' : 'Nessun movimento' }}</h2>
          <p class="mt-1 max-w-xs text-sm text-slate-500">{{ activeFilters ? 'Prova a modificare ricerca o filtri.' : 'Inserisci il primo movimento per iniziare a tenere sotto controllo il campo.' }}</p>
          <PButton v-if="!activeFilters" label="Inserisci movimento" icon="pi pi-plus" class="primary-cta mt-5" @click="router.push('/movimenti/nuovo')" />
          <PButton v-else label="Azzera filtri" icon="pi pi-filter-slash" text class="mt-3" @click="resetFilters" />
        </div>
      </template>
    </PCard>

    <PDialog v-model:visible="trashOpen" modal header="Cestino movimenti" class="summary-dialog w-[calc(100vw-2rem)] max-w-md">
      <div v-if="trashLoading" class="space-y-2"><MovementCardSkeleton v-for="n in 3" :key="n" /></div>
      <div v-else-if="!deletedMovements.length" class="py-6 text-center text-sm font-semibold text-slate-500">Nessun movimento nel cestino.</div>
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
  </main>
</template>
