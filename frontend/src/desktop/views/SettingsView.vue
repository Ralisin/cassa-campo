<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { api } from '@/api'
import PageHeader from '@/desktop/components/PageHeader.vue'

const router = useRouter()
const saving = ref(false)
const loading = ref(true)
const error = ref('')
const success = ref(false)
const euro = new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' })

const CATEGORY_LABELS = { vitto: 'Vitto', alloggio: 'Alloggio', trasporti: 'Trasporti', varie: 'Varie' }
const settings = reactive({
  camp_year: new Date().getFullYear(),
  camp_name: 'Campo',
  participants: 0,
  quota_per_person: 0,
  cash_initial: 0,
  category_budgets: { vitto: 0, alloggio: 0, trasporti: 0, varie: 0 },
})
const calculatedBudget = computed(() => Number(settings.participants) * Number(settings.quota_per_person))
const calculatedBankInitial = computed(() => calculatedBudget.value - Number(settings.cash_initial))
const budgetCategories = computed(() => Object.keys(settings.category_budgets))

async function load() {
  loading.value = true
  error.value = ''
  try {
    Object.assign(settings, await api.get('/settings'))
  } catch (cause) {
    if (cause?.status !== 404) error.value = cause instanceof Error ? cause.message : 'Caricamento non riuscito'
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  error.value = ''
  success.value = false
  try {
    await api.put('/settings', settings)
    success.value = true
    window.setTimeout(() => (success.value = false), 2500)
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : 'Salvataggio non riuscito'
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <PageHeader title="Impostazioni" subtitle="Dati del campo, saldi iniziali e preventivi">
      <template #actions>
        <PButton label="Riepilogo" icon="pi pi-chart-pie" outlined @click="router.push('/riepilogo')" />
        <PButton label="Salva" icon="pi pi-check" class="dk-topbar__cta" :loading="saving" @click="save" />
      </template>
    </PageHeader>

    <PMessage v-if="success" severity="success" size="small" class="mb-3">Impostazioni salvate.</PMessage>
    <PMessage v-if="error" severity="error" size="small" class="mb-3">{{ error }}</PMessage>

    <div class="dk-form-grid">
      <div class="dk-stack">
        <section class="dk-card">
          <h3 class="dk-card__title mb-4"><i class="pi pi-calendar dk-card__title-icon" /> Dati del campo</h3>
          <div class="dk-field-row">
            <div class="dk-field">
              <label for="camp-name">Nome campo</label>
              <PInputText id="camp-name" v-model="settings.camp_name" placeholder="Es. Campo estivo" fluid />
            </div>
            <div class="dk-field">
              <label for="camp-year">Anno</label>
              <PInputNumber id="camp-year" v-model="settings.camp_year" :min="2000" :max="2100" :use-grouping="false" fluid />
            </div>
          </div>
        </section>

        <section class="dk-card">
          <h3 class="dk-card__title mb-4"><i class="pi pi-wallet dk-card__title-icon" /> Partecipanti e saldi iniziali</h3>
          <p class="dk-card__subtitle mb-3">La disponibilità su carta viene calcolata automaticamente.</p>
          <div class="dk-field-row">
            <div class="dk-field">
              <label for="participants">Numero paganti</label>
              <PInputNumber id="participants" v-model="settings.participants" :min="0" :use-grouping="false" fluid />
            </div>
            <div class="dk-field">
              <label for="quota">Quota per ragazzo</label>
              <PInputNumber id="quota" v-model="settings.quota_per_person" mode="currency" currency="EUR" locale="it-IT" :min="0" fluid />
            </div>
          </div>
          <div class="dk-field">
            <label for="cash-initial">Contanti iniziali</label>
            <PInputNumber id="cash-initial" v-model="settings.cash_initial" mode="currency" currency="EUR" locale="it-IT" :min="0" :max="calculatedBudget" fluid />
          </div>
        </section>

        <section class="dk-card">
          <h3 class="dk-card__title mb-4"><i class="pi pi-chart-bar dk-card__title-icon" /> Preventivo per categoria</h3>
          <div class="dk-field-row">
            <div v-for="category in budgetCategories" :key="category" class="dk-field">
              <label :for="`budget-${category}`">{{ CATEGORY_LABELS[category] ?? category }}</label>
              <PInputNumber :id="`budget-${category}`" v-model="settings.category_budgets[category]" mode="currency" currency="EUR" locale="it-IT" :min="0" fluid />
            </div>
          </div>
        </section>
      </div>

      <div class="dk-card" style="position: sticky; top: 84px">
        <h3 class="dk-card__title mb-4"><i class="pi pi-calculator dk-card__title-icon" /> Riepilogo calcolato</h3>
        <div class="dk-define">
          <div class="dk-define__row"><i class="pi pi-users" /><span class="dk-define__label">Paganti</span><span class="dk-define__value">{{ settings.participants }}</span></div>
          <div class="dk-define__row"><i class="pi pi-briefcase" /><span class="dk-define__label">Spesa massima</span><span class="dk-define__value">{{ euro.format(calculatedBudget) }}</span></div>
          <div class="dk-define__row"><i class="pi pi-wallet" /><span class="dk-define__label">Contanti iniziali</span><span class="dk-define__value">{{ euro.format(Number(settings.cash_initial)) }}</span></div>
          <div class="dk-define__row"><i class="pi pi-credit-card" /><span class="dk-define__label">Carta iniziale</span><span class="dk-define__value">{{ euro.format(calculatedBankInitial) }}</span></div>
        </div>
        <PButton label="Salva impostazioni" icon="pi pi-check" class="dk-topbar__cta mt-5" :loading="saving" fluid @click="save" />
      </div>
    </div>
  </div>
</template>
