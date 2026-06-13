<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api'
import MovementCard from '@/_UI/components/MovementCard.vue'

const dashboard = ref(null)
const router = useRouter()
const euro = new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' })
const cashCards = computed(() => dashboard.value ? [
  { label: 'Cassa contanti', value: dashboard.value.cash_balance, icon: 'pi pi-wallet', severity: 'success' },
  { label: 'Cassa banca', value: dashboard.value.bank_balance, icon: 'pi pi-credit-card', severity: 'info' },
] : [])
onMounted(async () => (dashboard.value = await api.get('/dashboard')))
</script>

<template>
  <main v-if="dashboard" class="space-y-6">
    <section>
      <h2 class="section-title mb-2.5">Saldo casse</h2>
      <PDataView :value="cashCards">
        <template #list="{ items }"><div class="grid grid-cols-2 gap-3"><PCard v-for="item in items" :key="item.label" class="home-balance-card"><template #content><div class="flex flex-col gap-3"><PAvatar :icon="item.icon" size="large" shape="square" :class="item.severity === 'success' ? '!bg-emerald-50 !text-emerald-700' : '!bg-blue-50 !text-blue-700'" /><div><p class="text-xs font-bold text-slate-500">{{ item.label }}</p><p class="mt-1 text-lg font-black" :class="item.severity === 'success' ? 'text-emerald-700' : 'text-blue-700'">{{ euro.format(Number(item.value)) }}</p></div></div></template></PCard></div></template>
      </PDataView>
      <PButton label="Nuovo movimento" icon="pi pi-plus" size="large" fluid raised class="primary-cta !mt-4" @click="router.push('/movimenti/nuovo')" />
    </section>

    <section>
      <div class="mb-2.5 flex items-center justify-between"><h2 class="section-title">Movimenti di oggi</h2><PButton v-if="dashboard.today_movements.length" label="Vedi tutti" icon="pi pi-arrow-right" icon-pos="right" size="small" text @click="router.push('/movimenti')" /></div>
      <PDataView v-if="dashboard.today_movements.length" :value="dashboard.today_movements" class="movement-data-view">
        <template #list="{ items }"><div class="space-y-2"><MovementCard v-for="movement in items" :key="movement.id" :movement="movement" /></div></template>
      </PDataView>
      <PCard v-else class="home-empty-movements">
        <template #content>
          <div class="grid place-items-center py-4 text-center">
            <PAvatar icon="pi pi-receipt" size="large" shape="circle" class="!bg-emerald-50 !text-forest" />
            <p class="mt-3 text-sm font-black text-slate-800">Nessun movimento inserito oggi</p>
            <p class="mt-1 text-xs leading-relaxed text-slate-500">Puoi consultare lo storico completo dei movimenti.</p>
            <PButton label="Vedi tutti i movimenti" icon="pi pi-list" outlined class="mt-4" @click="router.push('/movimenti')" />
          </div>
        </template>
      </PCard>
    </section>
  </main>
  <div v-else class="space-y-3"><PCard v-for="n in 5" :key="n"><template #content><PSkeleton height="3rem" /></template></PCard></div>
</template>
