<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { api } from '@/api'
import { usePolling } from '@/composables/usePolling'
import ChartCard from '@/desktop/components/ChartCard.vue'
import KpiCard from '@/desktop/components/KpiCard.vue'
import MovementsTable from '@/desktop/components/MovementsTable.vue'
import PageHeader from '@/desktop/components/PageHeader.vue'
import RollingNumber from '@/desktop/components/RollingNumber.vue'

const router = useRouter()
const dashboard = ref(null)
const recentMovements = ref([])
const loadingMovements = ref(true)
const dashboardError = ref('')
const movementsError = ref('')
const euro = new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' })
const euroShort = new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })

const CATEGORY_COLORS = ['#347d59', '#d59d2b', '#1d4ed8', '#78bd98', '#b45309', '#0f766e']

const kpis = computed(() => {
  const d = dashboard.value
  if (!d) return []
  const spentPct = Number(d.max_budget) > 0 ? Math.round((Number(d.spent) / Number(d.max_budget)) * 100) : 0
  return [
    { label: 'Cassa contanti', value: euro.format(Number(d.cash_balance)), icon: 'pi pi-wallet', tone: 'emerald' },
    { label: 'Cassa banca', value: euro.format(Number(d.bank_balance)), icon: 'pi pi-credit-card', tone: 'blue' },
    { label: 'Spesa eseguita', value: euro.format(Number(d.spent)), icon: 'pi pi-receipt', tone: 'amber', hint: `${spentPct}% della spesa massima` },
    { label: 'Budget residuo', value: euro.format(Number(d.remaining_budget)), icon: 'pi pi-chart-line', tone: 'forest' },
  ]
})

function progressColor(spent, budget) {
  if (budget <= 0) return '#94a3b8'
  const ratio = spent / budget
  if (ratio > 1) return '#dc2626'
  if (ratio <= 0.5) return `hsl(${140 - ratio * 60} 55% 38%)`
  if (ratio <= 0.8) return `hsl(${80 - ((ratio - 0.5) / 0.3) * 35} 75% 42%)`
  return `hsl(${45 - ((ratio - 0.8) / 0.2) * 25} 88% 48%)`
}

const categoryRows = computed(() => (dashboard.value?.category_summaries ?? []).map((item) => {
  const budget = Number(item.budget)
  const spent = Number(item.spent)
  return {
    ...item,
    budget,
    spent,
    percentage: budget > 0 ? Math.min((spent / budget) * 100, 100) : 0,
    color: progressColor(spent, budget),
    overBudget: budget > 0 && spent > budget,
  }
}))

const hasCategoryData = computed(() => categoryRows.value.some((row) => row.spent > 0 || row.budget > 0))
// Slices with spend, used both for the doughnut and the centre overlay.
const donutRows = computed(() => categoryRows.value.filter((row) => row.spent > 0))
const donutTotals = computed(() => {
  const totalSpent = donutRows.value.reduce((sum, row) => sum + row.spent, 0)
  const totalBudget = categoryRows.value.reduce((sum, row) => sum + row.budget, 0)
  const pct = totalBudget > 0 ? Math.round((totalSpent / totalBudget) * 100) : null
  return { totalSpent, totalBudget, pct }
})

// Which slice the pointer is over (null = none → overall figure in the centre).
const hoverIndex = ref(null)
// Centre of the drawn doughnut, reported by the tracker plugin so the HTML
// overlay can sit exactly in the hole.
const centerPos = ref({ x: 0, y: 0 })

const centerData = computed(() => {
  const row = hoverIndex.value != null ? donutRows.value[hoverIndex.value] : null
  if (row) {
    let sub = 'nessun budget'
    let over = false
    if (row.budget > 0) {
      const diff = row.budget - row.spent
      over = diff < 0
      sub = over ? `sforato ${euroShort.format(-diff)}` : `restano ${euroShort.format(diff)}`
    }
    return { label: row.label.toUpperCase(), value: euroShort.format(row.spent), sub, over }
  }
  const { totalSpent, totalBudget, pct } = donutTotals.value
  return {
    label: 'SPESO',
    value: euroShort.format(totalSpent),
    sub: pct === null ? 'budget non impostato' : `${pct}% del budget`,
    over: pct !== null && totalSpent > totalBudget,
  }
})

const categoryChart = computed(() => ({
  data: {
    labels: donutRows.value.map((row) => row.label),
    datasets: [{ data: donutRows.value.map((row) => row.spent), backgroundColor: donutRows.value.map((_, i) => CATEGORY_COLORS[i % CATEGORY_COLORS.length]), borderWidth: 0, hoverOffset: 6 }],
  },
  options: {
    cutout: '64%',
    layout: { padding: { top: 4 } },
    // Hover drives the centre overlay instead of a tooltip.
    onHover: (event, elements) => { hoverIndex.value = elements.length ? elements[0].index : null },
    plugins: {
      legend: { position: 'bottom', labels: { boxWidth: 12, padding: 14, font: { size: 12 } } },
      tooltip: { enabled: false },
    },
    responsive: true,
    maintainAspectRatio: false,
  },
}))

// Keeps the overlay aligned with the doughnut hole (which sits above the legend).
const donutCenterTracker = {
  id: 'donutCenterTracker',
  afterDraw(chart) {
    const a = chart.chartArea
    if (!a) return
    const x = Math.round((a.left + a.right) / 2)
    const y = Math.round((a.top + a.bottom) / 2)
    if (centerPos.value.x !== x || centerPos.value.y !== y) centerPos.value = { x, y }
  },
}

// Spese giornaliere derivate dai movimenti recenti (ultimi 14 giorni con uscite).
const trend = computed(() => {
  const days = 14
  const buckets = new Map()
  const today = new Date()
  for (let i = days - 1; i >= 0; i -= 1) {
    const date = new Date(today)
    date.setDate(today.getDate() - i)
    buckets.set(date.toISOString().slice(0, 10), 0)
  }
  for (const movement of recentMovements.value) {
    if (movement.type !== 'uscita') continue
    if (buckets.has(movement.operation_date)) {
      buckets.set(movement.operation_date, buckets.get(movement.operation_date) + Number(movement.amount))
    }
  }
  const labels = [...buckets.keys()].map((iso) => new Intl.DateTimeFormat('it-IT', { day: '2-digit', month: '2-digit' }).format(new Date(`${iso}T00:00:00`)))
  return {
    hasData: [...buckets.values()].some((value) => value > 0),
    data: {
      labels,
      datasets: [{
        label: 'Uscite',
        data: [...buckets.values()],
        backgroundColor: 'rgba(52, 125, 89, 0.85)',
        hoverBackgroundColor: '#12372a',
        borderRadius: 6,
        maxBarThickness: 26,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: (ctx) => euro.format(ctx.parsed.y) } },
      },
      scales: {
        x: { grid: { display: false }, ticks: { font: { size: 11 } } },
        y: { beginAtZero: true, ticks: { callback: (value) => euroShort.format(value), font: { size: 11 } }, grid: { color: 'rgba(18,55,42,0.06)' } },
      },
    },
  }
})

async function loadDashboard() {
  dashboardError.value = ''
  try {
    dashboard.value = await api.get('/dashboard')
  } catch (cause) {
    dashboardError.value = cause instanceof Error ? cause.message : 'Caricamento dashboard non riuscito'
  }
}

async function loadMovements() {
  movementsError.value = ''
  try {
    const page = await api.get('/movements')
    recentMovements.value = page.items
  } catch (cause) {
    movementsError.value = cause instanceof Error ? cause.message : 'Caricamento movimenti recenti non riuscito'
  } finally {
    loadingMovements.value = false
  }
}

onMounted(() => {
  loadDashboard()
  loadMovements()
})
usePolling(loadDashboard)
usePolling(loadMovements, 12000)
</script>

<template>
  <div>
    <PageHeader title="Dashboard" subtitle="Panoramica economica del campo in tempo reale" />

    <template v-if="dashboard">
      <div class="dk-grid dk-grid--kpi">
        <KpiCard v-for="kpi in kpis" :key="kpi.label" v-bind="kpi" />
      </div>

      <section v-if="dashboard.anomalies?.length" class="dk-card dk-section">
        <header class="dk-card__head">
          <div>
            <h3 class="dk-card__title"><i class="pi pi-exclamation-triangle dk-card__title-icon" /> Da controllare</h3>
            <p class="dk-card__subtitle">Situazioni che meritano una verifica rapida</p>
          </div>
        </header>
        <div class="grid gap-2 md:grid-cols-2">
          <button
            v-for="item in dashboard.anomalies"
            :key="item.kind"
            type="button"
            class="dashboard-anomaly"
            :class="`dashboard-anomaly--${item.severity}`"
            @click="item.target && router.push(item.target)"
          >
            <span class="dashboard-anomaly__icon"><i class="pi pi-exclamation-triangle" /></span>
            <span class="min-w-0 flex-1 text-left">
              <strong>{{ item.title }}</strong>
              <small>{{ item.message }}</small>
            </span>
            <i v-if="item.target" class="pi pi-chevron-right text-xs text-slate-400" />
          </button>
        </div>
      </section>

      <div class="dk-grid dk-grid--dash dk-section">
        <div class="dk-stack">
          <ChartCard
            title="Andamento spese"
            subtitle="Uscite degli ultimi 14 giorni"
            icon="pi pi-chart-bar"
            :empty="!trend.hasData"
            empty-text="Nessuna uscita registrata di recente"
          >
            <div style="height: 260px">
              <PChart type="bar" :data="trend.data" :options="trend.options" />
            </div>
          </ChartCard>

          <section class="dk-card">
            <header class="dk-card__head">
              <div>
                <h3 class="dk-card__title"><i class="pi pi-clock dk-card__title-icon" /> Movimenti recenti</h3>
                <p class="dk-card__subtitle">Ultime registrazioni della cassa</p>
              </div>
              <PButton label="Vedi tutti" icon="pi pi-arrow-right" icon-pos="right" text size="small" @click="router.push('/movimenti')" />
            </header>
            <PMessage v-if="movementsError" severity="error" size="small" class="mb-3">
              {{ movementsError }}
              <PButton label="Riprova" icon="pi pi-refresh" size="small" text class="movement-inline-retry" @click="loadMovements" />
            </PMessage>
            <MovementsTable v-else :movements="recentMovements.slice(0, 8)" :loading="loadingMovements" compact empty-text="Nessun movimento registrato" />
          </section>
        </div>

        <div class="dk-stack">
          <ChartCard
            title="Spesa per categoria"
            subtitle="Ripartizione delle uscite"
            icon="pi pi-chart-pie"
            :empty="!categoryChart.data.labels.length"
            empty-text="Nessuna spesa categorizzata"
          >
            <div class="dk-donut" style="height: 260px">
              <PChart type="doughnut" :data="categoryChart.data" :options="categoryChart.options" :plugins="[donutCenterTracker]" />
              <div class="dk-donut__center" :style="{ left: `${centerPos.x}px`, top: `${centerPos.y}px` }">
                <span class="dk-donut__label">{{ centerData.label }}</span>
                <RollingNumber class="dk-donut__value" :value="centerData.value" />
                <span class="dk-donut__sub" :class="{ 'dk-donut__sub--over': centerData.over }">{{ centerData.sub }}</span>
              </div>
            </div>
          </ChartCard>

          <section class="dk-card">
            <header class="dk-card__head">
              <div>
                <h3 class="dk-card__title"><i class="pi pi-sliders-h dk-card__title-icon" /> Budget per categoria</h3>
                <p class="dk-card__subtitle">Speso su preventivo</p>
              </div>
            </header>
            <div v-if="hasCategoryData" class="space-y-4">
              <div v-for="row in categoryRows" :key="row.category">
                <div class="mb-1 flex items-center justify-between text-sm">
                  <span class="font-bold capitalize">{{ row.label }}</span>
                  <span class="font-semibold" :class="row.overBudget ? 'text-red-600' : 'text-slate-500'">
                    {{ euro.format(row.spent) }}<span class="text-slate-400"> / {{ row.budget > 0 ? euro.format(row.budget) : '—' }}</span>
                  </span>
                </div>
                <div class="dk-progress">
                  <span :style="{ width: `${row.percentage}%`, backgroundColor: row.color }" />
                </div>
              </div>
            </div>
            <p v-else class="dk-muted py-4 text-center text-sm">Imposta i preventivi dalle impostazioni per il confronto.</p>
          </section>
        </div>
      </div>
    </template>

    <template v-else-if="!dashboardError">
      <div class="dk-grid dk-grid--kpi">
        <article v-for="n in 4" :key="n" class="dk-kpi">
          <Skel circle w="3rem" h="3rem" />
          <div class="dk-kpi__body" style="flex: 1">
            <Skel w="55%" h="0.7rem" />
            <Skel w="70%" h="1.5rem" r="0.5rem" class="mt-2" />
          </div>
        </article>
      </div>

      <div class="dk-grid dk-grid--dash dk-section">
        <div class="dk-stack">
          <section class="dk-card">
            <header class="dk-card__head">
              <div><Skel w="9rem" h="1rem" /><Skel w="12rem" h="0.7rem" class="mt-2" /></div>
            </header>
            <div class="dk-skel-bars">
              <Skel v-for="n in 12" :key="n" w="100%" :h="`${30 + ((n * 37) % 70)}%`" r="6px 6px 0 0" />
            </div>
          </section>

          <section class="dk-card">
            <header class="dk-card__head">
              <div><Skel w="11rem" h="1rem" /><Skel w="9rem" h="0.7rem" class="mt-2" /></div>
              <Skel w="5rem" h="1.4rem" r="0.5rem" />
            </header>
            <div class="dk-skel-rows">
              <div v-for="n in 6" :key="n" class="dk-skel-row">
                <Skel circle w="2.1rem" h="2.1rem" />
                <div style="flex: 1"><Skel w="40%" h="0.8rem" /><Skel w="25%" h="0.65rem" class="mt-1.5" /></div>
                <Skel w="4.5rem" h="0.9rem" />
              </div>
            </div>
          </section>
        </div>

        <div class="dk-stack">
          <section class="dk-card">
            <header class="dk-card__head">
              <div><Skel w="10rem" h="1rem" /><Skel w="8rem" h="0.7rem" class="mt-2" /></div>
            </header>
            <div class="dk-skel-doughnut">
              <Skel circle w="11rem" h="11rem" />
              <div class="dk-skel-legend"><Skel v-for="n in 4" :key="n" w="4.5rem" h="0.7rem" /></div>
            </div>
          </section>

          <section class="dk-card">
            <header class="dk-card__head">
              <div><Skel w="11rem" h="1rem" /><Skel w="8rem" h="0.7rem" class="mt-2" /></div>
            </header>
            <div class="space-y-4">
              <div v-for="n in 4" :key="n">
                <div class="mb-1.5 flex items-center justify-between">
                  <Skel w="5rem" h="0.8rem" /><Skel w="7rem" h="0.8rem" />
                </div>
                <Skel w="100%" h="0.55rem" r="999px" />
              </div>
            </div>
          </section>
        </div>
      </div>
    </template>

    <template v-else>
      <section class="dk-card dk-section text-center">
        <PAvatar icon="pi pi-exclamation-triangle" size="large" shape="circle" class="!bg-red-50 !text-red-600" />
        <h2 class="mt-3 text-lg font-black text-slate-900">Dashboard non disponibile</h2>
        <p class="mx-auto mt-1 max-w-md text-sm text-slate-500">{{ dashboardError }}</p>
        <PButton label="Riprova" icon="pi pi-refresh" class="mt-4" @click="loadDashboard" />
      </section>
    </template>
  </div>
</template>
