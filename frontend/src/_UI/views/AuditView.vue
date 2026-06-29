<script setup>
import { onMounted, ref } from 'vue'

import { api } from '@/api'

const logs = ref([])
const loading = ref(true)
const error = ref('')
const dateFormatter = new Intl.DateTimeFormat('it-IT', { dateStyle: 'medium', timeStyle: 'short' })

async function load() {
  loading.value = true
  error.value = ''
  try {
    logs.value = await api.get('/audit')
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : 'Caricamento audit non riuscito'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <main class="space-y-3">
    <PMessage v-if="error" severity="error" size="small">
      {{ error }}
      <PButton label="Riprova" icon="pi pi-refresh" size="small" text class="movement-inline-retry" @click="load" />
    </PMessage>

    <div v-if="loading" class="space-y-2">
      <PCard v-for="n in 5" :key="n"><template #content><Skel w="60%" h="0.9rem" /><Skel w="40%" h="0.7rem" class="mt-2" /></template></PCard>
    </div>

    <PCard v-else-if="!logs.length" class="movements-empty">
      <template #content>
        <div class="grid place-items-center py-8 text-center">
          <PAvatar icon="pi pi-history" size="xlarge" shape="circle" class="!bg-emerald-50 !text-forest" />
          <h2 class="mt-4 text-base font-black text-slate-800">Nessun evento registrato</h2>
        </div>
      </template>
    </PCard>

    <template v-else>
      <article v-for="item in logs" :key="item.id" class="audit-item">
        <span class="audit-item__icon"><i class="pi pi-history" /></span>
        <span class="min-w-0 flex-1">
          <strong>{{ item.summary }}</strong>
          <small>{{ item.user_name || 'Sistema' }} · {{ dateFormatter.format(new Date(item.created_at)) }}</small>
        </span>
      </article>
    </template>
  </main>
</template>
