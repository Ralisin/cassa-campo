<script setup>
import { computed, onMounted, reactive, ref } from 'vue'

import { api } from '@/api'
import PageHeader from '@/desktop/components/PageHeader.vue'

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
        <PButton label="Salva" icon="pi pi-check" class="dk-topbar__cta" :loading="saving" @click="save" />
      </template>
    </PageHeader>

    <PMessage v-if="success" severity="success" size="small" class="mb-3">Impostazioni salvate.</PMessage>
    <PMessage v-if="error" severity="error" size="small" class="mb-3">{{ error }}</PMessage>

    <div v-if="loading" class="dk-form-grid">
      <div class="dk-stack">
        <section v-for="card in 3" :key="card" class="dk-card">
          <Skel w="11rem" h="1.05rem" class="mb-4" />
          <div class="dk-field-row">
            <div v-for="n in 2" :key="n" class="dk-field"><Skel w="6rem" h="0.75rem" /><Skel w="100%" h="2.75rem" class="mt-2" /></div>
          </div>
        </section>
      </div>
      <div class="dk-card">
        <Skel w="12rem" h="1.05rem" class="mb-4" />
        <div class="dk-define">
          <div v-for="n in 4" :key="n" class="dk-define__row"><Skel circle w="1.1rem" h="1.1rem" /><Skel w="7rem" h="0.8rem" style="flex: 1" /><Skel w="5rem" h="0.85rem" /></div>
        </div>
        <Skel w="100%" h="2.75rem" r="0.7rem" class="mt-5" />
      </div>
    </div>

    <div v-else class="dk-form-grid">
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
