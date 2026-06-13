<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api'
import MovementCard from '@/_UI/components/MovementCard.vue'

const movements = ref([])
const router = useRouter()
const query = ref('')
const type = ref('tutti')
const method = ref('tutti')
const creator = ref('tutti')
const reimbursement = ref('tutti')
const collapsedDates = ref(new Set())
const filtersCollapsed = ref(false)
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
const creators = computed(() => [
  { label: 'Tutti gli utenti', value: 'tutti' },
  ...Array.from(
    new Map(
      movements.value.map((movement) => [
        movement.created_by,
        { label: movement.creator_name, value: movement.created_by },
      ]),
    ).values(),
  ).sort((first, second) => first.label.localeCompare(second.label, 'it')),
])
const activeFilters = computed(() => [
  query.value.trim(),
  type.value !== 'tutti',
  method.value !== 'tutti',
  creator.value !== 'tutti',
  reimbursement.value !== 'tutti',
].filter(Boolean).length)
const filtered = computed(() => movements.value.filter((movement) => {
  const text = `${movement.supplier} ${movement.notes ?? ''} ${movement.creator_name} ${movement.creator_email}`.toLowerCase()
  return text.includes(query.value.toLowerCase())
    && (type.value === 'tutti' || movement.type === type.value)
    && (method.value === 'tutti' || movement.payment_method === method.value)
    && (creator.value === 'tutti' || movement.created_by === creator.value)
    && (
      reimbursement.value === 'tutti'
      || (reimbursement.value === 'nessuno' && !movement.reimbursement_status)
      || movement.reimbursement_status === reimbursement.value
    )
}))
const grouped = computed(() => filtered.value.reduce((groups, movement) => {
  groups[movement.operation_date] ??= []
  groups[movement.operation_date].push(movement)
  return groups
}, {}))
onMounted(async () => (movements.value = await api.get('/movements')))

function resetFilters() {
  query.value = ''
  type.value = 'tutti'
  method.value = 'tutti'
  creator.value = 'tutti'
  reimbursement.value = 'tutti'
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
            <span class="block text-[11px] font-medium text-slate-500">{{ filtered.length }} risultati</span>
          </span>
          <span v-if="activeFilters" class="movement-filters-toggle__count">{{ activeFilters }} attivi</span>
          <span class="movement-filters-toggle__chevron" :class="{ 'movement-filters-toggle__chevron--collapsed': filtersCollapsed }"><i class="pi pi-chevron-up" /></span>
        </button>
        <div v-if="activeFilters" class="movement-filters-clear">
          <span>{{ activeFilters }} {{ activeFilters === 1 ? 'filtro attivo' : 'filtri attivi' }}</span>
          <PButton label="Azzera" icon="pi pi-filter-slash" size="small" text class="movement-filters-clear__button" @click="resetFilters" />
        </div>

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
    <PCard v-if="!filtered.length" class="movements-empty">
      <template #content>
        <div class="grid place-items-center py-8 text-center">
          <PAvatar icon="pi pi-receipt" size="xlarge" shape="circle" class="!bg-emerald-50 !text-forest" />
          <h2 class="mt-4 text-base font-black text-slate-800">{{ movements.length ? 'Nessun risultato' : 'Nessun movimento' }}</h2>
          <p class="mt-1 max-w-xs text-sm text-slate-500">{{ movements.length ? 'Prova a modificare ricerca o filtri.' : 'Inserisci il primo movimento per iniziare a tenere sotto controllo il campo.' }}</p>
          <PButton v-if="!movements.length" label="Inserisci movimento" icon="pi pi-plus" class="primary-cta mt-5" @click="router.push('/movimenti/nuovo')" />
          <PButton v-else label="Azzera filtri" icon="pi pi-filter-slash" text class="mt-3" @click="resetFilters" />
        </div>
      </template>
    </PCard>
  </main>
</template>
