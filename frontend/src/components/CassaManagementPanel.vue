<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useConfirm } from 'primevue/useconfirm'

import { api } from '@/api'
import { useSessionStore } from '@/stores/session'

const emit = defineEmits(['changed'])

const session = useSessionStore()
const confirm = useConfirm()

const BRANCHES = ['L/C', 'E/G', 'R/S', 'CoCa', 'Gruppo']
const KIND_LABELS = { campo: 'Campo', anno: 'Anno' }
const KIND_OPTIONS = [
  { label: 'Cassa Campo', value: 'campo' },
  { label: 'Cassa Anno', value: 'anno' },
]

const casse = ref([])
const loading = ref(false)
const busy = ref(false)
const error = ref('')
const dialogOpen = ref(false)
const form = reactive({
  unit: session.activeCassa?.unit ?? 'E/G',
  kind: 'anno',
  year: new Date().getFullYear(),
})

const openKindsForSelectedUnit = computed(() => new Set(
  casse.value
    .filter((item) => !item.is_closed && item.unit === form.unit)
    .map((item) => item.kind),
))
const canCreateSelectedKind = computed(() => !openKindsForSelectedUnit.value.has(form.kind))
const availableKinds = computed(() => KIND_OPTIONS.map((item) => ({
  ...item,
  disabled: openKindsForSelectedUnit.value.has(item.value),
})))
const membershipRoles = computed(() => new Map(
  session.memberships.map((item) => [item.cassa_id, item.role]),
))

function statusLabel(cassa) {
  return cassa.is_closed ? 'Chiusa' : 'Aperta'
}

function kindLabel(kind) {
  return KIND_LABELS[kind] ?? kind
}

function canCloseCassa(cassa) {
  if (session.isSystemAdmin) return true
  return ['admin', 'cashier'].includes(membershipRoles.value.get(cassa.id))
}

function contextOptions() {
  return session.cassaManagementContextId ? { cassaId: session.cassaManagementContextId } : {}
}

async function loadCasse() {
  if (!session.canManageCasse || !session.cassaManagementContextId) return
  loading.value = true
  error.value = ''
  try {
    casse.value = await api.get('/casse', contextOptions())
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : 'Caricamento casse non riuscito'
  } finally {
    loading.value = false
  }
}

function openCreate() {
  form.unit = session.activeCassa?.unit ?? session.memberships[0]?.unit ?? 'E/G'
  const used = new Set(
    casse.value
      .filter((item) => !item.is_closed && item.unit === form.unit)
      .map((item) => item.kind),
  )
  const firstAvailable = KIND_OPTIONS.find((item) => !used.has(item.value))
  form.kind = firstAvailable?.value ?? 'anno'
  form.year = new Date().getFullYear()
  error.value = ''
  dialogOpen.value = true
}

async function createCassa() {
  if (!canCreateSelectedKind.value) return
  busy.value = true
  error.value = ''
  try {
    await api.post('/casse', {
      unit: form.unit,
      kind: form.kind,
      year: Number(form.year),
    }, contextOptions())
    dialogOpen.value = false
    await session.loadUser()
    await loadCasse()
    emit('changed')
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : 'Creazione cassa non riuscita'
  } finally {
    busy.value = false
  }
}

function askClose(event, cassa) {
  confirm.require({
    target: event.currentTarget,
    header: 'Chiudi cassa',
    message: `Chiudere ${kindLabel(cassa.kind)} ${cassa.year}? Rimarrà consultabile ma non modificabile.`,
    icon: 'pi pi-lock',
    rejectLabel: 'Annulla',
    acceptLabel: 'Chiudi',
    acceptClass: 'p-button-danger',
    accept: () => closeCassa(cassa),
  })
}

async function closeCassa(cassa) {
  busy.value = true
  error.value = ''
  try {
    await api.put(`/casse/${cassa.id}/close`, {}, contextOptions())
    await session.loadUser()
    await loadCasse()
    emit('changed')
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : 'Chiusura cassa non riuscita'
  } finally {
    busy.value = false
  }
}

onMounted(loadCasse)
</script>

<template>
  <section v-if="session.canManageCasse" class="cassa-manage">
    <div class="cassa-manage__head">
      <div>
        <p class="cassa-manage__eyebrow">Gestione casse</p>
        <h2 class="cassa-manage__title">Casse del gruppo</h2>
      </div>
      <PButton
        label="Nuova cassa"
        icon="pi pi-plus"
        size="small"
        :disabled="!session.cassaManagementContextId"
        @click="openCreate"
      />
    </div>

    <PMessage v-if="error" severity="error" size="small" class="mt-3">{{ error }}</PMessage>

    <div v-if="loading" class="cassa-manage__empty">Caricamento casse...</div>
    <div v-else-if="!casse.length" class="cassa-manage__empty">Nessuna cassa trovata.</div>
    <div v-else class="cassa-manage__list">
      <article v-for="cassa in casse" :key="cassa.id" class="cassa-manage__row">
        <div class="min-w-0">
          <p class="cassa-manage__row-title">{{ cassa.unit }} · {{ kindLabel(cassa.kind) }} {{ cassa.year }}</p>
          <p class="cassa-manage__row-meta">
            {{ statusLabel(cassa) }}<template v-if="cassa.closed_at"> · chiusa il {{ cassa.closed_at }}</template>
          </p>
        </div>
        <div class="cassa-manage__actions">
          <PTag :value="statusLabel(cassa)" :severity="cassa.is_closed ? 'secondary' : 'success'" />
          <PButton
            v-if="!cassa.is_closed && canCloseCassa(cassa)"
            icon="pi pi-lock"
            text
            rounded
            severity="danger"
            aria-label="Chiudi cassa"
            :loading="busy"
            @click="askClose($event, cassa)"
          />
        </div>
      </article>
    </div>

    <PDialog v-model:visible="dialogOpen" modal header="Nuova cassa" class="cassa-manage__dialog" :style="{ width: 'min(28rem, calc(100vw - 2rem))' }">
      <form class="space-y-4" @submit.prevent="createCassa">
        <div class="dk-field">
          <label for="cassa-kind">Tipo</label>
          <PSelect id="cassa-kind" v-model="form.kind" :options="availableKinds" option-label="label" option-value="value" option-disabled="disabled" fluid />
          <small v-if="!canCreateSelectedKind" class="field-error">Esiste già una cassa aperta di questo tipo.</small>
        </div>
        <div class="dk-field">
          <label for="cassa-unit">Unità</label>
          <PSelect id="cassa-unit" v-model="form.unit" :options="BRANCHES" fluid />
        </div>
        <div class="dk-field">
          <label for="cassa-year">Anno</label>
          <PInputNumber id="cassa-year" v-model="form.year" :min="2000" :max="2100" :use-grouping="false" fluid />
        </div>
        <div class="flex justify-end gap-2">
          <PButton type="button" label="Annulla" severity="secondary" text @click="dialogOpen = false" />
          <PButton type="submit" label="Crea" icon="pi pi-plus" :loading="busy" :disabled="!canCreateSelectedKind" />
        </div>
      </form>
    </PDialog>
  </section>
</template>

<style scoped>
.cassa-manage {
  width: 100%;
  margin-top: 0.5rem;
  padding: 1rem;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 0.75rem;
  background: #fff;
}

.cassa-manage__head,
.cassa-manage__row,
.cassa-manage__actions {
  display: flex;
  align-items: center;
}

.cassa-manage__head,
.cassa-manage__row {
  justify-content: space-between;
  gap: 1rem;
}

.cassa-manage__eyebrow {
  color: #64748b;
  font-size: 0.68rem;
  font-weight: 900;
  text-transform: uppercase;
}

.cassa-manage__title {
  margin-top: 0.15rem;
  color: #020617;
  font-size: 1rem;
  font-weight: 900;
}

.cassa-manage__list {
  margin-top: 0.75rem;
  overflow: hidden;
  border: 1px solid #e2e8f0;
  border-radius: 0.6rem;
}

.cassa-manage__row {
  min-height: 3.8rem;
  padding: 0.75rem;
  border-top: 1px solid #e2e8f0;
}

.cassa-manage__row:first-child {
  border-top: 0;
}

.cassa-manage__row-title {
  overflow: hidden;
  color: #0f172a;
  font-size: 0.9rem;
  font-weight: 900;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cassa-manage__row-meta,
.cassa-manage__empty {
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 600;
}

.cassa-manage__empty {
  margin-top: 0.75rem;
}

.cassa-manage__actions {
  flex: 0 0 auto;
  gap: 0.35rem;
}

@media (max-width: 520px) {
  .cassa-manage__head,
  .cassa-manage__row {
    align-items: stretch;
    flex-direction: column;
  }

  .cassa-manage__actions {
    justify-content: space-between;
  }
}
</style>
