<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '@/api'

const data = ref(null)
const loading = ref(true)
const error = ref('')
const search = ref('')
const euro = new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' })
const date = new Intl.DateTimeFormat('it-IT', { dateStyle: 'medium' })
const payments = computed(() => (data.value?.payments ?? []).filter((item) =>
  item.person.toLocaleLowerCase('it-IT').includes(search.value.trim().toLocaleLowerCase('it-IT'))))

onMounted(async () => {
  try { data.value = await api.get('/movements/annual-dues') }
  catch (cause) { error.value = cause instanceof Error ? cause.message : 'Impossibile caricare le quote' }
  finally { loading.value = false }
})
</script>

<template>
  <div class="mx-auto w-full max-w-5xl p-4 md:p-8">
    <div class="mb-6 flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-black text-forest">Quote anno</h1>
        <p class="mt-1 text-sm text-slate-600">Pagamenti registrati per la cassa annuale attiva</p>
      </div>
      <RouterLink v-if="data" to="/movimenti/nuovo?annual_dues=1"><PButton label="Registra quota" icon="pi pi-plus" /></RouterLink>
    </div>
    <PMessage v-if="error" severity="error">{{ error }}</PMessage>
    <div v-else-if="loading" class="dk-card">Caricamento…</div>
    <template v-else>
      <div class="dk-card mb-5">
        <p class="text-sm font-semibold text-slate-600">Quote pagate / ragazzi registrati</p>
        <p class="mt-1 text-3xl font-black text-forest">{{ data.paid }} / {{ data.registered }}</p>
        <p class="mt-2 text-sm text-slate-600">Da pagare: {{ Math.max(0, data.registered - data.paid) }} · Quota: {{ euro.format(Number(data.quota_per_person)) }}</p>
      </div>
      <div class="dk-card">
        <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 class="text-lg font-bold text-forest">Chi ha pagato</h2>
          <PInputText v-model="search" placeholder="Cerca ragazzo/a" aria-label="Cerca ragazzo o ragazza" />
        </div>
        <p v-if="!payments.length" class="text-sm text-slate-600">{{ search ? 'Nessun risultato.' : 'Nessuna quota registrata.' }}</p>
        <div v-else class="divide-y divide-slate-100">
          <RouterLink v-for="item in payments" :key="item.movement_id" :to="`/movimenti/${item.movement_id}`" class="flex flex-wrap items-center justify-between gap-3 py-3 text-sm hover:text-emerald-700">
            <strong class="text-forest">{{ item.person }}</strong>
            <span>{{ date.format(new Date(`${item.operation_date}T00:00:00`)) }}</span>
            <span class="capitalize">{{ item.payment_method }}</span>
            <strong>{{ euro.format(Number(item.amount)) }}</strong>
            <i class="pi pi-angle-right" aria-hidden="true" />
          </RouterLink>
        </div>
      </div>
    </template>
  </div>
</template>
