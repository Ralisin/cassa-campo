<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '@/api'

const route = useRoute()
const router = useRouter()
const email = ref('')
const password = ref('')
const repeatPassword = ref('')
const loading = ref(false)
const message = ref('')
const error = ref('')
const token = computed(() => typeof route.query.token === 'string' ? route.query.token : '')
const confirming = computed(() => Boolean(token.value))

async function submit() {
  loading.value = true
  message.value = ''
  error.value = ''
  try {
    if (confirming.value) {
      if (password.value !== repeatPassword.value) {
        error.value = 'Le password non coincidono.'
        return
      }
      await api.post('/auth/password-reset/confirm', {
        token: token.value,
        new_password: password.value,
      })
      message.value = 'Password aggiornata. Ora puoi accedere.'
      window.setTimeout(() => router.push('/login'), 900)
    } else {
      await api.post('/auth/password-reset/request', { email: email.value })
      message.value = 'Se l’email è registrata, riceverai un link per reimpostare la password.'
    }
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : 'Operazione non riuscita'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <div class="login-shell">
      <header class="login-brand">
        <PAvatar icon="pi pi-key" size="xlarge" shape="circle" class="login-brand__icon" />
        <div>
          <p class="text-[11px] font-black uppercase tracking-[0.24em] text-emerald-200">Cassa Campo</p>
          <h1 class="mt-1 text-3xl font-black text-white">Password</h1>
          <p class="mt-1 text-sm text-emerald-100/80">{{ confirming ? 'Scegli una nuova password.' : 'Ricevi un link di reimpostazione.' }}</p>
        </div>
      </header>

      <PCard class="login-card">
        <template #content>
          <form class="space-y-4" @submit.prevent="submit">
            <template v-if="confirming">
              <div>
                <label for="password">Nuova password</label>
                <PPassword id="password" v-model="password" toggle-mask required fluid />
              </div>
              <div>
                <label for="repeat-password">Ripeti password</label>
                <PPassword id="repeat-password" v-model="repeatPassword" :feedback="false" toggle-mask required fluid />
              </div>
            </template>
            <div v-else>
              <label for="email">Email</label>
              <PIconField><PInputIcon class="pi pi-envelope" /><PInputText id="email" v-model="email" type="email" autocomplete="email" placeholder="nome@email.it" required fluid /></PIconField>
            </div>
            <PMessage v-if="message" severity="success" size="small">{{ message }}</PMessage>
            <PMessage v-if="error" severity="error" size="small">{{ error }}</PMessage>
            <PButton type="submit" :label="confirming ? 'Aggiorna password' : 'Invia link'" icon="pi pi-arrow-right" icon-pos="right" size="large" :loading="loading" fluid raised class="primary-cta login-submit" />
            <PButton type="button" label="Torna al login" icon="pi pi-arrow-left" text fluid @click="router.push('/login')" />
          </form>
        </template>
      </PCard>
    </div>
  </main>
</template>
