<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { useSessionStore } from '@/stores/session'

const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)
const router = useRouter()
const session = useSessionStore()

async function submit() {
  loading.value = true
  error.value = ''
  try {
    await session.login(email.value, password.value)
    router.push('/')
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : 'Accesso non riuscito'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <div class="login-shell">
      <header class="login-brand">
        <PAvatar icon="pi pi-wallet" size="xlarge" shape="circle" class="login-brand__icon" />
        <div>
          <p class="text-[11px] font-black uppercase tracking-[0.24em] text-emerald-200">Gestione economica</p>
          <h1 class="mt-1 text-3xl font-black text-white">Cassa Campo</h1>
          <p class="mt-1 text-sm text-emerald-100/80">Tutto il campo, senza perdere uno scontrino.</p>
        </div>
      </header>

      <PCard class="login-card">
        <template #content>
          <div>
            <h2 class="text-lg font-black text-slate-900">Bentornato</h2>
            <p class="mt-1 text-sm text-slate-500">Accedi per gestire movimenti e saldi.</p>
          </div>
          <form class="mt-6 space-y-4" @submit.prevent="submit">
            <div>
              <label for="email">Email</label>
              <PIconField><PInputIcon class="pi pi-envelope" /><PInputText id="email" v-model="email" type="email" autocomplete="email" placeholder="nome@email.it" required fluid /></PIconField>
            </div>
            <div>
              <label for="password">Password</label>
              <PPassword id="password" v-model="password" :feedback="false" toggle-mask autocomplete="current-password" placeholder="La tua password" required fluid />
            </div>
            <PMessage v-if="error" severity="error" size="small">{{ error }}</PMessage>
            <PButton type="submit" label="Entra" icon="pi pi-arrow-right" icon-pos="right" size="large" :loading="loading" fluid raised class="primary-cta login-submit" />
          </form>
        </template>
      </PCard>

      <p class="login-footer"><i class="pi pi-lock" /> Accesso riservato allo staff del campo</p>
    </div>
  </main>
</template>
