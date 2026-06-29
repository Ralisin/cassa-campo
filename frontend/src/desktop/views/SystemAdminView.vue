<script setup>
import { computed, onMounted, ref } from 'vue'
import { useConfirm } from 'primevue/useconfirm'
import { useRouter } from 'vue-router'

import { api } from '@/api'
import PageHeader from '@/desktop/components/PageHeader.vue'
import { useSessionStore } from '@/stores/session'

const router = useRouter()
const session = useSessionStore()
const confirm = useConfirm()

const groups = ref([])
const loading = ref(false)
const error = ref('')
const cassaBusy = ref(false)
const cassaDialogOpen = ref(false)
const cassaError = ref('')
const cassaGroup = ref(null)
const cassaForm = ref({
  unit: 'E/G',
  kind: 'anno',
  year: new Date().getFullYear(),
})
const passwordBusy = ref(false)
const passwordMessage = ref('')
const passwordError = ref('')
const passwordExpanded = ref(false)
const passwordForm = ref({
  current_password: '',
  new_password: '',
  repeat_password: '',
})

const euro = new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' })
const KIND_LABELS = { campo: 'Campo', anno: 'Anno' }
const BRANCHES = ['L/C', 'E/G', 'R/S', 'CoCa', 'Gruppo']
const KIND_OPTIONS = [
  { label: 'Cassa Campo', value: 'campo' },
  { label: 'Cassa Anno', value: 'anno' },
]
const totalGroups = computed(() => groups.value.length)
const totalCasse = computed(() => groups.value.reduce((sum, group) => sum + group.casse.length, 0))
const totalUsers = computed(() => groups.value.reduce((sum, group) => sum + group.users_count, 0))
const cassaKindOptions = computed(() => {
  const used = cassaGroup.value ? openKinds(cassaGroup.value, cassaForm.value.unit) : new Set()
  return KIND_OPTIONS.map((item) => ({ ...item, disabled: used.has(item.value) }))
})
const canCreateCassaKind = computed(() => !cassaKindOptions.value.find((item) => item.value === cassaForm.value.kind)?.disabled)

async function loadOverview() {
  loading.value = true
  error.value = ''
  try {
    const data = await api.get('/system/overview')
    groups.value = data.groups
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : 'Caricamento non riuscito'
  } finally {
    loading.value = false
  }
}

function openCassa(group, cassa, path = '/') {
  session.setSystemCassa({
    cassa_id: cassa.id,
    unit: cassa.unit,
    kind: cassa.kind,
    status: cassa.status,
    year: cassa.year,
    opened_at: cassa.opened_at,
    closed_at: cassa.closed_at,
    is_closed: cassa.is_closed,
    group_id: group.id,
    group_slug: group.slug,
    group_name: group.name,
  })
  router.push(path)
}

function openKinds(group, unit = null) {
  return new Set(
    group.casse
      .filter((item) => !item.is_closed && (!unit || item.unit === unit))
      .map((item) => item.kind),
  )
}

function groupContext(group) {
  return group.casse[0] ? { cassaId: group.casse[0].id } : {}
}

function openCreateCassa(group) {
  cassaGroup.value = group
  const unit = group.casse[0]?.unit ?? 'E/G'
  const used = openKinds(group, unit)
  const firstAvailable = KIND_OPTIONS.find((item) => !used.has(item.value))
  cassaForm.value = {
    unit,
    kind: firstAvailable?.value ?? 'anno',
    year: new Date().getFullYear(),
  }
  cassaError.value = ''
  cassaDialogOpen.value = true
}

async function createCassa() {
  if (!cassaGroup.value) return
  cassaBusy.value = true
  cassaError.value = ''
  try {
    await api.post('/casse', {
      unit: cassaForm.value.unit,
      kind: cassaForm.value.kind,
      year: Number(cassaForm.value.year),
    }, groupContext(cassaGroup.value))
    cassaDialogOpen.value = false
    await loadOverview()
  } catch (cause) {
    cassaError.value = cause instanceof Error ? cause.message : 'Creazione cassa non riuscita'
  } finally {
    cassaBusy.value = false
  }
}

function confirmCloseCassa(event, group, cassa) {
  confirm.require({
    target: event.currentTarget,
    message: `Chiudere ${KIND_LABELS[cassa.kind] ?? cassa.kind} ${cassa.year} di ${group.name}?`,
    icon: 'pi pi-lock',
    header: 'Conferma chiusura cassa',
    rejectLabel: 'Annulla',
    acceptLabel: 'Chiudi cassa',
    acceptClass: 'p-button-danger',
    accept: () => closeCassa(cassa),
  })
}

function confirmDeleteCassa(event, group, cassa) {
  confirm.require({
    target: event.currentTarget,
    message: `Eliminare definitivamente ${KIND_LABELS[cassa.kind] ?? cassa.kind} ${cassa.year} di ${group.name}? Verranno rimossi movimenti, rimborsi e ricevute collegati.`,
    icon: 'pi pi-trash',
    header: 'Conferma eliminazione cassa',
    rejectLabel: 'Annulla',
    acceptLabel: 'Elimina cassa',
    acceptClass: 'p-button-danger',
    accept: () => deleteCassa(cassa),
  })
}

async function closeCassa(cassa) {
  cassaBusy.value = true
  cassaError.value = ''
  try {
    await api.put(`/casse/${cassa.id}/close`, {}, { cassaId: cassa.id })
    await loadOverview()
  } catch (cause) {
    cassaError.value = cause instanceof Error ? cause.message : 'Chiusura cassa non riuscita'
  } finally {
    cassaBusy.value = false
  }
}

async function deleteCassa(cassa) {
  cassaBusy.value = true
  cassaError.value = ''
  try {
    await api.delete(`/system/casse/${cassa.id}`)
    if (session.activeCassaId === cassa.id) session.setSystemCassa(null)
    await loadOverview()
  } catch (cause) {
    cassaError.value = cause instanceof Error ? cause.message : 'Eliminazione cassa non riuscita'
  } finally {
    cassaBusy.value = false
  }
}

function confirmDeleteGroup(event, group) {
  confirm.require({
    target: event.currentTarget,
    message: `Eliminare definitivamente ${group.name} con tutte le sue casse, utenti e movimenti?`,
    icon: 'pi pi-exclamation-triangle',
    header: 'Conferma eliminazione gruppo',
    rejectLabel: 'Annulla',
    acceptLabel: 'Elimina gruppo',
    acceptClass: 'p-button-danger',
    accept: () => deleteGroup(group),
  })
}

async function deleteGroup(group) {
  await api.delete(`/system/groups/${group.id}`)
  groups.value = groups.value.filter((item) => item.id !== group.id)
}

async function changePassword() {
  passwordMessage.value = ''
  passwordError.value = ''
  if (passwordForm.value.new_password !== passwordForm.value.repeat_password) {
    passwordError.value = 'Le nuove password non coincidono'
    return
  }
  passwordBusy.value = true
  try {
    await api.put('/auth/password', {
      current_password: passwordForm.value.current_password,
      new_password: passwordForm.value.new_password,
    })
    passwordForm.value = { current_password: '', new_password: '', repeat_password: '' }
    passwordMessage.value = 'Password aggiornata'
  } catch (cause) {
    passwordError.value = cause instanceof Error ? cause.message : 'Aggiornamento non riuscito'
  } finally {
    passwordBusy.value = false
  }
}

onMounted(loadOverview)
</script>

<template>
  <div>
    <PageHeader title="Sistema" subtitle="Gestione globale gruppi e casse">
      <template #actions>
        <PButton label="Aggiorna" icon="pi pi-refresh" outlined :loading="loading" @click="loadOverview" />
      </template>
    </PageHeader>

    <PMessage v-if="error" severity="error" class="mb-4">{{ error }}</PMessage>

    <div class="mb-5 grid gap-4 md:grid-cols-3">
      <div class="dk-card">
        <p class="text-xs font-black uppercase text-slate-400">Gruppi</p>
        <p class="mt-2 text-3xl font-black text-slate-950">{{ totalGroups }}</p>
      </div>
      <div class="dk-card">
        <p class="text-xs font-black uppercase text-slate-400">Casse</p>
        <p class="mt-2 text-3xl font-black text-slate-950">{{ totalCasse }}</p>
      </div>
      <div class="dk-card">
        <p class="text-xs font-black uppercase text-slate-400">Utenti gestiti</p>
        <p class="mt-2 text-3xl font-black text-slate-950">{{ totalUsers }}</p>
      </div>
    </div>

    <div class="grid gap-5 xl:grid-cols-[minmax(0,1fr)_24rem]">
      <aside class="dk-card system-password-card self-start xl:order-2">
        <button
          type="button"
          class="system-password-card__toggle"
          :aria-expanded="passwordExpanded"
          aria-controls="system-password-form"
          @click="passwordExpanded = !passwordExpanded"
        >
          <span class="min-w-0">
            <span class="system-password-card__title">Password profilo sistema</span>
            <span class="system-password-card__hint">Aggiorna le credenziali dell'accesso globale</span>
          </span>
          <i class="pi pi-chevron-down system-password-card__chevron" :class="{ 'system-password-card__chevron--open': passwordExpanded }" />
        </button>
        <form
          id="system-password-form"
          class="system-password-card__form mt-4 space-y-4"
          :class="{ 'system-password-card__form--collapsed': !passwordExpanded }"
          @submit.prevent="changePassword"
        >
          <div class="dk-field">
            <label for="current-password">Password attuale</label>
            <PPassword id="current-password" v-model="passwordForm.current_password" :feedback="false" toggle-mask required fluid />
          </div>
          <div class="dk-field">
            <label for="new-password">Nuova password</label>
            <PPassword id="new-password" v-model="passwordForm.new_password" toggle-mask required fluid />
          </div>
          <div class="dk-field">
            <label for="repeat-password">Ripeti nuova password</label>
            <PPassword id="repeat-password" v-model="passwordForm.repeat_password" :feedback="false" toggle-mask required fluid />
          </div>
          <PMessage v-if="passwordMessage" severity="success" size="small">{{ passwordMessage }}</PMessage>
          <PMessage v-if="passwordError" severity="error" size="small">{{ passwordError }}</PMessage>
          <PButton type="submit" label="Aggiorna password" icon="pi pi-key" :loading="passwordBusy" fluid />
        </form>
      </aside>

      <section class="space-y-4 xl:order-1">
        <div v-if="loading && !groups.length" class="dk-card">
          <Skel w="12rem" h="1.2rem" />
          <Skel v-for="n in 4" :key="n" w="100%" h="4.2rem" r="0.7rem" class="mt-4" />
        </div>

        <div v-else-if="!groups.length" class="dk-card text-center">
          <PAvatar icon="pi pi-inbox" size="large" shape="circle" class="!bg-slate-100 !text-slate-400" />
          <p class="mt-3 font-black text-slate-900">Nessun gruppo creato</p>
        </div>

        <article v-for="group in groups" v-else :key="group.id" class="dk-card">
          <div class="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 pb-4">
            <div class="min-w-0">
              <h2 class="truncate text-lg font-black text-slate-950">{{ group.name }}</h2>
              <p class="mt-1 text-sm font-semibold text-slate-500">{{ group.email_domain }} · {{ group.users_count }} utenti</p>
            </div>
            <div class="flex flex-wrap justify-end gap-2">
              <PButton label="Nuova cassa" icon="pi pi-plus" outlined :disabled="!group.casse.length" @click="openCreateCassa(group)" />
              <PButton label="Elimina gruppo" icon="pi pi-trash" severity="danger" outlined @click="confirmDeleteGroup($event, group)" />
            </div>
          </div>

          <div class="system-casse-list mt-4 overflow-hidden rounded-lg border border-slate-100">
            <div class="system-casse-list__head bg-slate-50 px-4 py-2 text-xs font-black uppercase text-slate-400">
              <span>Cassa</span>
              <span class="text-right">Contanti</span>
              <span class="text-right">Banca</span>
              <span class="text-right">Azioni</span>
            </div>
            <div v-if="!group.casse.length" class="px-4 py-5 text-sm font-semibold text-slate-500">
              Nessuna cassa creata per questo gruppo.
            </div>
            <div
              v-for="cassa in group.casse"
              :key="cassa.id"
              class="system-casse-list__row border-t border-slate-100 px-4 py-3"
            >
              <div class="system-casse-list__unit min-w-0">
                <p class="font-black text-slate-900">{{ cassa.unit }}</p>
                <p class="text-xs font-semibold text-slate-400">
                  {{ KIND_LABELS[cassa.kind] ?? cassa.kind }} {{ cassa.year }} · {{ cassa.movements_count }} movimenti
                </p>
                <PTag v-if="cassa.is_closed" value="Chiusa" severity="secondary" class="mt-1" />
              </div>
              <p class="system-casse-list__amount text-sm font-black text-slate-900">
                <span>Contanti</span>{{ euro.format(Number(cassa.cash_balance)) }}
              </p>
              <p class="system-casse-list__amount text-sm font-black text-slate-900">
                <span>Banca</span>{{ euro.format(Number(cassa.bank_balance)) }}
              </p>
              <div class="system-casse-list__actions flex justify-end gap-2">
                <PButton v-if="!cassa.is_closed" icon="pi pi-lock" text rounded severity="danger" aria-label="Chiudi cassa" :loading="cassaBusy" @click="confirmCloseCassa($event, group, cassa)" />
                <PButton icon="pi pi-trash" text rounded severity="danger" aria-label="Elimina cassa" :loading="cassaBusy" @click="confirmDeleteCassa($event, group, cassa)" />
                <PButton icon="pi pi-list" text rounded aria-label="Movimenti" @click="openCassa(group, cassa, '/movimenti')" />
                <PButton icon="pi pi-arrow-right" rounded aria-label="Apri cassa" @click="openCassa(group, cassa)" />
              </div>
            </div>
          </div>
        </article>
      </section>
    </div>

    <PDialog v-model:visible="cassaDialogOpen" modal header="Nuova cassa" :style="{ width: 'min(28rem, calc(100vw - 2rem))' }">
      <form class="space-y-4" @submit.prevent="createCassa">
        <PMessage v-if="cassaError" severity="error" size="small">{{ cassaError }}</PMessage>
        <div class="dk-field">
          <label for="system-cassa-kind">Tipo</label>
          <PSelect id="system-cassa-kind" v-model="cassaForm.kind" :options="cassaKindOptions" option-label="label" option-value="value" option-disabled="disabled" fluid />
          <small v-if="!canCreateCassaKind" class="field-error">Esiste già una cassa aperta di questo tipo.</small>
        </div>
        <div class="dk-field">
          <label for="system-cassa-unit">Unità</label>
          <PSelect id="system-cassa-unit" v-model="cassaForm.unit" :options="BRANCHES" fluid />
        </div>
        <div class="dk-field">
          <label for="system-cassa-year">Anno</label>
          <PInputNumber id="system-cassa-year" v-model="cassaForm.year" :min="2000" :max="2100" :use-grouping="false" fluid />
        </div>
        <div class="flex justify-end gap-2">
          <PButton type="button" label="Annulla" severity="secondary" text @click="cassaDialogOpen = false" />
          <PButton type="submit" label="Crea" icon="pi pi-plus" :loading="cassaBusy" :disabled="!canCreateCassaKind" />
        </div>
      </form>
    </PDialog>
  </div>
</template>

<style scoped>
.system-password-card__toggle {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  text-align: left;
}

.system-password-card__title,
.system-password-card__hint {
  display: block;
}

.system-password-card__title {
  color: #020617;
  font-size: 1rem;
  font-weight: 900;
}

.system-password-card__hint {
  margin-top: 0.2rem;
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 600;
  line-height: 1.35;
}

.system-password-card__chevron {
  display: none;
  flex: 0 0 auto;
  color: #64748b;
  transition: transform 0.18s ease;
}

.system-password-card__chevron--open {
  transform: rotate(180deg);
}

.system-casse-list__head,
.system-casse-list__row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 9rem 9rem 12rem;
  align-items: center;
}

.system-casse-list__amount {
  text-align: right;
}

.system-casse-list__amount span {
  display: none;
}

@media (max-width: 767px) {
  .system-password-card__chevron {
    display: inline-block;
  }

  .system-password-card__form--collapsed {
    display: none;
  }

  .system-casse-list {
    border: 0;
    border-radius: 0;
  }

  .system-casse-list__head {
    display: none;
  }

  .system-casse-list__row {
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 0.75rem;
    margin-top: 0.75rem;
    border: 1px solid #e2e8f0;
    border-radius: 0.8rem;
    background: #fff;
  }

  .system-casse-list__unit {
    grid-column: 1 / -1;
  }

  .system-casse-list__amount {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 0.15rem;
    text-align: left;
  }

  .system-casse-list__amount span {
    display: inline;
    color: #94a3b8;
    font-size: 0.66rem;
    font-weight: 900;
    text-transform: uppercase;
  }

  .system-casse-list__actions {
    grid-column: 1 / -1;
    justify-content: stretch;
  }

  .system-casse-list__actions :deep(.p-button) {
    flex: 1 1 0;
  }
}

@media (min-width: 768px) {
  .system-password-card__form--collapsed {
    display: block;
  }
}
</style>
