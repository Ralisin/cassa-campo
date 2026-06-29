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

const features = [
  { icon: 'pi pi-bolt', text: 'Movimenti, saldi e rimborsi sempre allineati' },
  { icon: 'pi pi-chart-pie', text: 'Dashboard e report con grafici in tempo reale' },
  { icon: 'pi pi-file-excel', text: 'Esportazione del bilancio in Excel con un clic' },
]

async function submit() {
  loading.value = true
    error.value = ''
  try {
    await session.login(email.value, password.value)
    router.push(session.isSystemAdmin ? '/system' : '/')
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : 'Accesso non riuscito'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="dk-login">
    <aside class="dk-login__aside">
      <div class="dk-login__brand">
        <img src="/icon.svg" alt="" />
        <div>
          <div class="dk-login__brand-name">Cassa Campo</div>
          <div class="dk-login__brand-sub">Gestione economica</div>
        </div>
      </div>

      <div class="dk-login__pitch">
        <h2>Tutto il campo, senza perdere uno scontrino.</h2>
        <p>Il gestionale della cassa per il tuo gruppo scout: entrate, uscite, rimborsi e bilanci sotto controllo, da qualsiasi dispositivo.</p>
      </div>

      <div class="dk-login__features">
        <div v-for="feature in features" :key="feature.text" class="dk-login__feature">
          <i :class="feature.icon" />
          <span>{{ feature.text }}</span>
        </div>
      </div>
    </aside>

    <section class="dk-login__panel">
      <div class="dk-login__card">
        <h1>Bentornato</h1>
        <p class="dk-login__lead">Accedi per gestire movimenti e saldi.</p>

        <form class="mt-7 space-y-4" @submit.prevent="submit">
          <div class="dk-field">
            <label for="email">Email</label>
            <PIconField>
              <PInputIcon class="pi pi-envelope" />
              <PInputText id="email" v-model="email" type="email" autocomplete="email" placeholder="nome@email.it" required fluid />
            </PIconField>
          </div>
          <div class="dk-field">
            <label for="password">Password</label>
            <PIconField>
              <PInputIcon class="pi pi-lock" />
              <PPassword id="password" v-model="password" :feedback="false" toggle-mask autocomplete="current-password" placeholder="La tua password" required fluid />
            </PIconField>
          </div>
          <PMessage v-if="error" severity="error" size="small">{{ error }}</PMessage>
          <PButton type="submit" label="Entra" icon="pi pi-arrow-right" icon-pos="right" size="large" :loading="loading" fluid raised class="dk-topbar__cta" />
        </form>

        <p class="mt-6 flex items-center justify-center gap-2 text-xs font-semibold text-slate-400">
          <i class="pi pi-lock" /> Accesso riservato allo staff del campo
        </p>
      </div>
    </section>
  </div>
</template>
