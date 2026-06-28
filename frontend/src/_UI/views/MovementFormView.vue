<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api, uploadReceipt } from '@/api'
import { queueMovement } from '@/offlineQueue'
import { useSessionStore } from '@/stores/session'

const route = useRoute()
const router = useRouter()
const session = useSessionStore()
const editing = computed(() => typeof route.params.id === 'string')
const saving = ref(false)
const error = ref('')
const offlineNotice = ref('')
const submitted = ref(false)
const receiptInput = ref(null)
const receiptCameraInput = ref(null)
const selectedReceipts = ref([])
const balanceTypes = [
  { label: 'Campo', value: 'C' },
  { label: 'Ordinario', value: 'O' },
  { label: 'Autofinanziamento', value: 'A' },
]
const categories = [
  { label: 'Vitto', value: 'vitto' },
  { label: 'Alloggio', value: 'alloggio' },
  { label: 'Trasporti', value: 'trasporti' },
  { label: 'Varie', value: 'varie' },
]
const movementTypes = [
  { label: 'Entrata', value: 'entrata', icon: 'pi pi-arrow-down-left' },
  { label: 'Uscita', value: 'uscita', icon: 'pi pi-arrow-up-right' },
]
const paymentMethods = computed(() => [
  { label: 'Contanti', value: 'contanti', icon: 'pi pi-wallet' },
  { label: 'Carta', value: 'carta', icon: 'pi pi-credit-card', disabled: form.needs_reimbursement },
])
const operationDate = computed({
  get: () => (form.operation_date ? new Date(`${form.operation_date}T00:00:00`) : null),
  set: (date) => {
    if (!date) {
      form.operation_date = ''
      return
    }
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    form.operation_date = `${year}-${month}-${day}`
  },
})
const form = reactive({
  operation_date: new Date().toISOString().slice(0, 10),
  type: 'uscita',
  payment_method: 'contanti',
  supplier: '',
  unit: session.activeCassa?.unit ?? '',
  balance_type: 'C',
  category: 'varie',
  amount: 0,
  notes: '',
  needs_reimbursement: false,
})
const amountInvalid = computed(() => submitted.value && (!Number.isFinite(Number(form.amount)) || Number(form.amount) <= 0))
const supplierInvalid = computed(() => submitted.value && !form.supplier.trim())
const dateInvalid = computed(() => submitted.value && !form.operation_date)
const notesInvalid = computed(() => submitted.value && !form.notes?.trim())
const categoryInvalid = computed(() => submitted.value && form.type === 'uscita' && !form.category)
const receiptSummary = computed(() => selectedReceipts.value.reduce((sum, file) => sum + file.size, 0))

watch(
  () => form.needs_reimbursement,
  (enabled) => {
    if (enabled) {
      form.type = 'uscita'
      form.payment_method = 'contanti'
    }
  },
)

watch(
  () => [form.type, form.payment_method],
  ([type, method]) => {
    if (type !== 'uscita' || method !== 'contanti') form.needs_reimbursement = false
  },
)

watch(
  () => form.type,
  (value, previous) => {
    if (!value) form.type = previous || 'uscita'
    if (value === 'entrata') form.category = null
    else if (!form.category) form.category = 'varie'
  },
)

watch(
  () => form.payment_method,
  (value, previous) => {
    if (!value) form.payment_method = previous || 'contanti'
  },
)

onMounted(async () => {
  if (!session.user) await session.loadUser()
  if (!editing.value) {
    form.unit = session.activeCassa?.unit ?? ''
    return
  }
  const movement = await api.get(`/movements/${route.params.id}`)
  if (!session.isOperator && movement.created_by !== session.user?.id) {
    router.replace(`/movimenti/${route.params.id}`)
    return
  }
  Object.assign(form, movement, { amount: Number(movement.amount) })
  // The unit always follows the active cassa.
  form.unit = session.activeCassa?.unit ?? form.unit
})

async function submit() {
  submitted.value = true
  error.value = ''
  offlineNotice.value = ''
  if (amountInvalid.value || supplierInvalid.value || dateInvalid.value || notesInvalid.value || categoryInvalid.value) {
    return
  }
  saving.value = true
  const payload = { ...form }
  try {
    let saved
    try {
      saved = editing.value
        ? await api.put(`/movements/${route.params.id}`, payload)
        : await api.post('/movements', payload)
    } catch (cause) {
      const canQueue = !editing.value && (!navigator.onLine || cause instanceof TypeError)
      if (!canQueue) throw cause

      await queueMovement(payload, selectedReceipts.value, session.user?.id, session.activeCassaId)
      offlineNotice.value = 'Movimento salvato sul dispositivo. Verrà sincronizzato appena torna la connessione.'
      window.setTimeout(() => router.push('/movimenti'), 900)
      return
    }

    for (const file of selectedReceipts.value) {
      await uploadReceipt(saved.id, file)
    }
    router.push(selectedReceipts.value.length ? `/movimenti/${saved.id}` : '/movimenti')
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : 'Salvataggio non riuscito'
  } finally {
    saving.value = false
  }
}

function selectReceipts(event) {
  const files = Array.from(event.target.files ?? [])
  selectedReceipts.value = [...selectedReceipts.value, ...files]
  event.target.value = ''
}

function removeReceipt(index) {
  selectedReceipts.value = selectedReceipts.value.filter((_, itemIndex) => itemIndex !== index)
}

function formatBytes(bytes) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}
</script>

<template>
  <main>
    <PCard class="movement-form-card">
      <template #content>
        <form class="movement-form space-y-3" novalidate @submit.prevent="submit">
          <section class="space-y-2.5 rounded-xl bg-slate-50 p-2.5">
            <div>
              <label>Tipo movimento</label>
              <div class="exclusive-button-group" role="radiogroup" aria-label="Tipo movimento">
                <PButton
                  v-for="option in movementTypes"
                  :key="option.value"
                  :label="option.label"
                  :icon="option.icon"
                  :aria-pressed="form.type === option.value"
                  class="exclusive-button"
                  :class="[
                    `exclusive-button--${option.value}`,
                    { 'exclusive-button--selected': form.type === option.value },
                  ]"
                  @click="form.type = option.value"
                />
              </div>
            </div>
            <div>
              <label>Metodo di pagamento</label>
              <div class="exclusive-button-group" role="radiogroup" aria-label="Metodo di pagamento">
                <PButton
                  v-for="option in paymentMethods"
                  :key="option.value"
                  :label="option.label"
                  :icon="option.icon"
                  :disabled="option.disabled"
                  :aria-pressed="form.payment_method === option.value"
                  class="exclusive-button"
                  :class="{ 'exclusive-button--selected': form.payment_method === option.value }"
                  @click="form.payment_method = option.value"
                />
              </div>
            </div>
          </section>

          <section class="space-y-3">
            <div class="movement-form-field-pair">
              <div><label for="date">Data operazione <span class="required-mark">*</span></label><PDatePicker id="date" v-model="operationDate" date-format="dd/mm/yy" show-icon icon-display="input" :manual-input="false" :invalid="dateInvalid" fluid /><small v-if="dateInvalid" class="field-error">La data operazione è obbligatoria.</small></div>
              <div><label for="supplier">Fornitore <span class="required-mark">*</span></label><PInputText id="supplier" v-model="form.supplier" :invalid="supplierInvalid" placeholder="Es. Esselunga" fluid /><small v-if="supplierInvalid" class="field-error">Il fornitore è obbligatorio.</small></div>
            </div>
            <div class="movement-form-field-pair">
              <div><label for="unit">Unità</label><PInputText id="unit" v-model="form.unit" disabled fluid /><small class="mt-1 block text-[0.67rem] font-medium text-slate-500">Definita dalla cassa attiva.</small></div>
              <div><label for="balance-type">Bilancio</label><PSelect id="balance-type" v-model="form.balance_type" :options="balanceTypes" option-label="label" option-value="value" fluid /></div>
            </div>
            <div v-if="form.type === 'uscita'" class="movement-form-field-pair">
              <div>
                <label for="category">Categoria <span class="required-mark">*</span></label>
                <PSelect id="category" v-model="form.category" :options="categories" option-label="label" option-value="value" :invalid="categoryInvalid" placeholder="Seleziona una categoria" fluid />
                <small v-if="categoryInvalid" class="field-error">La categoria è obbligatoria per le uscite.</small>
              </div>
              <div><label for="amount">Importo <span class="required-mark">*</span></label><PInputNumber id="amount" v-model="form.amount" mode="currency" currency="EUR" locale="it-IT" :min="0.01" :invalid="amountInvalid" fluid /><small v-if="amountInvalid" class="field-error">Inserisci un importo maggiore di zero.</small></div>
            </div>
            <div v-else><label for="amount">Importo <span class="required-mark">*</span></label><PInputNumber id="amount" v-model="form.amount" mode="currency" currency="EUR" locale="it-IT" :min="0.01" :invalid="amountInvalid" fluid /><small v-if="amountInvalid" class="field-error">Inserisci un importo maggiore di zero.</small></div>
            <div><label for="notes">Note <span class="required-mark">*</span></label><PTextarea id="notes" v-model="form.notes" rows="2" :invalid="notesInvalid" placeholder="Descrivi il movimento..." fluid /><small v-if="notesInvalid" class="field-error">Le note sono obbligatorie.</small></div>
          </section>

          <label
            class="reimbursement-option"
            :class="{ 'reimbursement-option--active': form.needs_reimbursement }"
            for="reimbursement"
          >
            <PAvatar icon="pi pi-replay" shape="circle" class="reimbursement-option__icon" />
            <span class="min-w-0 flex-1">
              <strong class="block text-sm text-forest">Da rimborsare</strong>
              <span class="block text-xs font-normal leading-relaxed text-slate-600">
                Spesa anticipata personalmente, registrata in contanti.
              </span>
            </span>
            <PToggleSwitch v-model="form.needs_reimbursement" input-id="reimbursement" />
          </label>

          <section class="receipt-upload-panel">
            <input
              ref="receiptInput"
              type="file"
              accept="image/jpeg,image/png,application/pdf"
              multiple
              class="hidden"
              @change="selectReceipts"
            >
            <input
              ref="receiptCameraInput"
              type="file"
              accept="image/*"
              capture="environment"
              class="hidden"
              @change="selectReceipts"
            >
            <div class="receipt-upload-panel__header">
              <PAvatar icon="pi pi-paperclip" shape="circle" class="!bg-emerald-50 !text-forest" />
              <div class="min-w-0 flex-1">
                <strong class="block text-sm text-forest">Scontrini</strong>
                <span class="block text-xs font-normal leading-relaxed text-slate-600">
                  Scatta una foto o allega PDF, PNG e JPEG.
                </span>
              </div>
              <div class="receipt-upload-panel__actions">
                <PButton type="button" icon="pi pi-camera" rounded aria-label="Scatta foto scontrino" class="receipt-upload-panel__button" @click="receiptCameraInput?.click()" />
                <PButton type="button" icon="pi pi-plus" rounded aria-label="Aggiungi file scontrino" class="receipt-upload-panel__button receipt-upload-panel__button--secondary" @click="receiptInput?.click()" />
              </div>
            </div>
            <div v-if="selectedReceipts.length" class="receipt-upload-panel__list">
              <div v-for="(file, index) in selectedReceipts" :key="`${file.name}-${file.size}-${index}`" class="receipt-upload-item">
                <i :class="file.type === 'application/pdf' ? 'pi pi-file-pdf' : 'pi pi-image'" class="text-slate-500" />
                <span class="min-w-0 flex-1">
                  <strong class="block truncate text-xs text-slate-800">{{ file.name }}</strong>
                  <span class="block text-[11px] font-semibold text-slate-500">{{ formatBytes(file.size) }}</span>
                </span>
                <PButton type="button" icon="pi pi-times" text rounded severity="secondary" aria-label="Rimuovi scontrino" class="!h-8 !w-8" @click="removeReceipt(index)" />
              </div>
              <p class="text-right text-[11px] font-bold text-slate-500">Totale {{ formatBytes(receiptSummary) }}</p>
            </div>
          </section>
          <PMessage v-if="offlineNotice" severity="success" size="small">{{ offlineNotice }}</PMessage>
          <PMessage v-if="error" severity="error" size="small">{{ error }}</PMessage>
          <div class="movement-form-actions">
            <PButton type="submit" label="Salva movimento" icon="pi pi-check-circle" size="large" :loading="saving" fluid raised class="primary-cta" />
          </div>
        </form>
      </template>
    </PCard>
  </main>
</template>
