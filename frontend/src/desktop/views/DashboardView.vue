<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { api } from '@/api'
import { usePolling } from '@/composables/usePolling'
import ChartCard from '@/desktop/components/ChartCard.vue'
import KpiCard from '@/desktop/components/KpiCard.vue'
import MovementsTable from '@/desktop/components/MovementsTable.vue'
import PageHeader from '@/desktop/components/PageHeader.vue'

const router = useRouter()
const dashboard = ref(null)
const recentMovements = ref([])
const loadingMovements = ref(true)
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
const categoryChart = computed(() => {
  const rows = categoryRows.value.filter((row) => row.spent > 0)
  return {
    data: {
      labels: rows.map((row) => row.label),
      datasets: [{ data: rows.map((row) => row.spent), backgroundColor: rows.map((_, i) => CATEGORY_COLORS[i % CATEGORY_COLORS.length]), borderWidth: 0 }],
    },
    options: {
      cutout: '62%',
      plugins: {
        legend: { position: 'bottom', labels: { boxWidth: 12, padding: 14, font: { size: 12 } } },
        tooltip: { callbacks: { label: (ctx) => `${ctx.label}: ${euro.format(ctx.parsed)}` } },
      },
      responsive: true,
      maintainAspectRatio: false,
    },
  }
})

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
  dashboard.value = await api.get('/dashboard')
}

async function loadMovements() {
  try {
    const page = await api.get('/movements')
    recentMovements.value = page.items
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
    <PageHeader title="Dashboard" subtitle="Panoramica economica del campo in tempo reale">
      <template #actions>
        <PButton label="Riepilogo" icon="pi pi-chart-pie" outlined @click="router.push('/riepilogo')" />
        <PButton label="Nuovo movimento" icon="pi pi-plus" class="dk-topbar__cta" @click="router.push('/movimenti/nuovo')" />
      </template>
    </PageHeader>

    <template v-if="dashboard">
      <div class="dk-grid dk-grid--kpi">
        <KpiCard v-for="kpi in kpis" :key="kpi.label" v-bind="kpi" />
      </div>

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
            <MovementsTable :movements="recentMovements.slice(0, 8)" :loading="loadingMovements" compact empty-text="Nessun movimento registrato" />
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
            <div style="height: 260px">
              <PChart type="doughnut" :data="categoryChart.data" :options="categoryChart.options" />
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

    <div v-else class="dk-grid dk-grid--kpi">
      <PSkeleton v-for="n in 4" :key="n" height="6rem" class="dk-skeleton" />
    </div>
  </div>
</template>
