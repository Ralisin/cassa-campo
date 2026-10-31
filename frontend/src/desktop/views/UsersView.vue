<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useConfirm } from 'primevue/useconfirm'

import { api } from '@/api'
import PageHeader from '@/desktop/components/PageHeader.vue'
import { useSessionStore } from '@/stores/session'

const session = useSessionStore()
const router = useRouter()
const confirm = useConfirm()
const users = ref([])
const casse = ref([])
const loading = ref(true)
const dialogVisible = ref(false)
const saving = ref(false)
const deletingId = ref(null)
const submitted = ref(false)
const error = ref('')
const editingId = ref(null)
const branches = ['L/C', 'E/G', 'R/S', 'CoCa', 'Gruppo']
const roles = [
  { label: 'Utente', value: 'user' },
  { label: 'Cassiere', value: 'cashier' },
  { label: 'Admin', value: 'admin' },
]
const ROLE_LABELS = { admin: 'Admin', cashier: 'Cassiere', user: 'Utente' }
const ROLE_SEVERITY = { admin: 'success', cashier: 'warn', user: 'secondary' }

const form = reactive({
  first_name: '',
  last_name: '',
  email: '',
  password: '',
  memberships: [],
})
const editing = computed(() => Boolean(editingId.value))
const nameInvalid = computed(() => submitted.value && !form.first_name.trim())
const lastNameInvalid = computed(() => submitted.value && !form.last_name.trim())
const emailInvalid = computed(() => submitted.value && !form.email.trim())
const passwordInvalid = computed(
  () => submitted.value && ((!editing.value || form.password) && form.password.length < 8),
)
const membershipsInvalid = computed(() => {
  if (!submitted.value) return false
  if (!form.memberships.length) return true
  const ids = form.memberships.map((item) => item.unit)
  return ids.some((id) => !id) || new Set(ids).size !== ids.length
})

const sortedUsers = computed(() =>
  [...users.value].sort((a, b) => {
    const selfId = session.user?.id
    if (a.id === selfId) return -1
    if (b.id === selfId) return 1
    return a.name.localeCompare(b.name, 'it', { sensitivity: 'base' })
  }),
)

const unitOptions = computed(() => [...new Set(casse.value.map((cassa) => cassa.unit))].sort((a, b) => branches.indexOf(a) - branches.indexOf(b)).map((unit) => ({ unit, label: unit })))

function availableUnits(index) {
  return unitOptions.value.filter((option) => option.unit === form.memberships[index].unit
    || !form.memberships.some((item, position) => position !== index && item.unit === option.unit))
}

function addMembership() {
  const next = unitOptions.value.find((option) => !form.memberships.some((item) => item.unit === option.unit))
  if (next) form.memberships.push({ unit: next.unit, role: 'user' })
}

function removeMembership(index) {
  form.memberships.splice(index, 1)
}

async function loadCasse() {
  casse.value = await api.get('/casse')
}

async function loadUsers() {
  users.value = await api.get('/users')
}

function openCreate() {
  editingId.value = null
  Object.assign(form, { first_name: '', last_name: '', email: '', password: '', memberships: [] })
  addMembership()
  submitted.value = false
  error.value = ''
  dialogVisible.value = true
}
function openEdit(user) {
  editingId.value = user.id
  Object.assign(form, {
    first_name: user.first_name ?? user.name.split(' ')[0],
    last_name: user.last_name ?? user.name.split(' ').slice(1).join(' '),
    email: user.email,
    password: '',
    memberships: user.memberships.length
      ? [...new Map(user.memberships.map((item) => [item.unit, { unit: item.unit, role: item.role }])).values()]
      : [{ unit: unitOptions.value[0]?.unit ?? null, role: 'user' }],
  })
  submitted.value = false
  error.value = ''
  dialogVisible.value = true
}

async function save() {
  submitted.value = true
  error.value = ''
  if (nameInvalid.value || lastNameInvalid.value || emailInvalid.value || passwordInvalid.value || membershipsInvalid.value) return
  saving.value = true
  try {
    const payload = {
      name: `${form.first_name.trim()} ${form.last_name.trim()}`,
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      email: form.email,
      memberships: form.memberships.map((item) => ({ unit: item.unit, role: item.role })),
    }
    if (!editing.value || form.password) payload.password = form.password
    if (editing.value) await api.put(`/users/${editingId.value}`, payload)
    else await api.post('/users', payload)
    await loadUsers()
    if (editingId.value === session.user?.id) {
      await session.loadUser()
      if (!session.isAdmin) {
        router.replace('/')
        return
      }
    }
    dialogVisible.value = false
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : 'Salvataggio non riuscito'
  } finally {
    saving.value = false
  }
}

function askDelete(event, user) {
  confirm.require({
    target: event.currentTarget,
    header: 'Elimina persona',
    message: `Eliminare ${user.name}? Perderà subito l’accesso; i movimenti già registrati resteranno consultabili.`,
    icon: 'pi pi-trash',
    rejectLabel: 'Annulla',
    acceptLabel: 'Elimina',
    acceptClass: 'p-button-danger',
    accept: () => deleteUser(user),
  })
}

async function deleteUser(user) {
  deletingId.value = user.id
  error.value = ''
  try {
    await api.delete(`/users/${user.id}`)
    await loadUsers()
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : 'Eliminazione non riuscita'
  } finally {
    deletingId.value = null
  }
}

function initials(name) {
  return name.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()
}
function roleLabel(role) {
  return ROLE_LABELS[role] ?? role
}

onMounted(async () => {
  try {
    await Promise.all([loadUsers(), loadCasse()])
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : 'Caricamento non riuscito'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <PageHeader title="Gestione utenti" :subtitle="`${users.length} profili abilitati`">
      <template #actions>
        <PButton label="Registra persona" icon="pi pi-user-plus" class="dk-topbar__cta" @click="openCreate" />
      </template>
    </PageHeader>

    <div class="dk-card">
      <PMessage v-if="error && !dialogVisible" severity="error" size="small">{{ error }}</PMessage>
      <div v-if="loading && !users.length" class="dk-skel-rows">
        <div v-for="n in 6" :key="n" class="dk-skel-row">
          <Skel circle w="2.1rem" h="2.1rem" />
          <div style="flex: 1"><Skel w="30%" h="0.85rem" /><Skel w="45%" h="0.65rem" class="mt-1.5" /></div>
          <div class="flex gap-1.5"><Skel w="5rem" h="1.4rem" r="0.5rem" /><Skel w="5rem" h="1.4rem" r="0.5rem" /></div>
          <Skel circle w="1.7rem" h="1.7rem" />
        </div>
      </div>
      <PDataTable v-else :value="sortedUsers" data-key="id" row-hover class="dk-table" :pt="{ bodyRow: { class: 'dk-table__row' } }" @row-click="(e) => openEdit(e.data)">
        <template #empty><div class="dk-table__empty"><i class="pi pi-users" /><span>Nessun utente registrato</span></div></template>
        <PColumn header="Persona">
          <template #body="{ data }">
            <div class="dk-mv">
              <PAvatar :label="initials(data.name)" shape="circle" class="!bg-slate-100 !font-black !text-forest" />
              <div class="min-w-0">
                <span class="dk-mv__name">
                  {{ data.name }}
                  <PTag v-if="data.id === session.user?.id" value="Tu" severity="secondary" class="ml-1" />
                </span>
                <span class="dk-mv__notes">{{ data.email }}</span>
              </div>
            </div>
          </template>
        </PColumn>
        <PColumn header="Unità e ruoli">
          <template #body="{ data }">
            <div class="flex flex-wrap gap-1.5">
              <PTag
                v-for="membership in [...new Map(data.memberships.map((item) => [item.unit, item])).values()]"
                :key="membership.unit"
                :value="`${membership.unit} · ${roleLabel(membership.role)}`"
                :severity="ROLE_SEVERITY[membership.role]"
              />
              <PTag v-if="!data.memberships.length" value="Nessuna cassa" severity="danger" />
            </div>
          </template>
        </PColumn>
        <PColumn header="" style="width: 7rem" :pt="{ headerContent: { class: 'justify-end' } }">
          <template #body="{ data }">
            <div class="dk-table__actions">
              <PButton icon="pi pi-pencil" text rounded size="small" aria-label="Modifica" @click.stop="openEdit(data)" />
              <PButton v-if="data.id !== session.user?.id" icon="pi pi-trash" text rounded size="small" severity="danger" :aria-label="`Elimina ${data.name}`" :loading="deletingId === data.id" @click.stop="askDelete($event, data)" />
            </div>
          </template>
        </PColumn>
      </PDataTable>
    </div>

    <PDialog v-model:visible="dialogVisible" modal :header="editing ? 'Modifica persona' : 'Registra persona'" class="summary-dialog user-dialog w-[30rem]">
      <form class="summary-dialog__form" novalidate @submit.prevent="save">
        <p class="summary-dialog__intro">
          <i :class="editing ? 'pi pi-user-edit' : 'pi pi-user-plus'" />
          {{ editing ? 'Aggiorna i dati e i ruoli per unità.' : 'Crea un accesso e assegna una o più unità.' }}
        </p>
        <div class="summary-dialog__field">
          <label for="user-first-name">Nome <span class="required-mark">*</span></label>
          <PInputText id="user-first-name" v-model="form.first_name" :invalid="nameInvalid" autocomplete="given-name" fluid />
          <small v-if="nameInvalid" class="field-error">Il nome è obbligatorio.</small>
        </div>
        <div class="summary-dialog__field">
          <label for="user-last-name">Cognome <span class="required-mark">*</span></label>
          <PInputText id="user-last-name" v-model="form.last_name" :invalid="lastNameInvalid" autocomplete="family-name" fluid />
          <small v-if="lastNameInvalid" class="field-error">Il cognome è obbligatorio.</small>
        </div>
        <div class="summary-dialog__field">
          <label for="user-email">Email <span class="required-mark">*</span></label>
          <PInputText id="user-email" v-model="form.email" type="email" :invalid="emailInvalid" fluid />
          <small v-if="emailInvalid" class="field-error">L’email è obbligatoria.</small>
          <small class="mt-1 block text-[0.67rem] font-medium text-slate-500">Deve appartenere al dominio del gruppo.</small>
        </div>
        <div class="summary-dialog__field">
          <div class="mb-1 flex items-center justify-between">
            <label>Unità e ruoli <span class="required-mark">*</span></label>
            <PButton type="button" label="Aggiungi" icon="pi pi-plus" text size="small" :disabled="form.memberships.length >= unitOptions.length" @click="addMembership" />
          </div>
          <div class="space-y-2">
            <div v-for="(membership, index) in form.memberships" :key="index" class="membership-row">
              <PSelect v-model="membership.unit" :options="availableUnits(index)" option-label="label" option-value="unit" class="membership-row__cassa" />
              <PSelect v-model="membership.role" :options="roles" option-label="label" option-value="value" class="membership-row__role" />
              <PButton type="button" icon="pi pi-times" text rounded severity="secondary" aria-label="Rimuovi unità" :disabled="form.memberships.length === 1" class="!h-9 !w-9" @click="removeMembership(index)" />
            </div>
          </div>
          <small v-if="membershipsInvalid" class="field-error">Assegna almeno una unità senza duplicati.</small>
        </div>
        <div class="summary-dialog__field">
          <label for="user-password">Password <span v-if="!editing" class="required-mark">*</span></label>
          <PPassword id="user-password" v-model="form.password" :feedback="false" toggle-mask :invalid="passwordInvalid" fluid />
          <small v-if="passwordInvalid" class="field-error">Inserisci almeno 8 caratteri.</small>
          <small v-else-if="editing" class="mt-1 block text-[0.67rem] font-medium text-slate-500">Lascia vuoto per mantenere la password attuale.</small>
        </div>
        <PMessage v-if="error" severity="error" size="small">{{ error }}</PMessage>
        <div class="summary-dialog__actions">
          <PButton type="button" label="Annulla" class="summary-dialog__cancel" @click="dialogVisible = false" />
          <PButton type="submit" :label="editing ? 'Salva modifiche' : 'Registra'" icon="pi pi-check" class="summary-dialog__submit" :loading="saving" />
        </div>
      </form>
    </PDialog>
  </div>
</template>

<style scoped>
.membership-row { display: flex; align-items: center; gap: 0.5rem; }
.membership-row__cassa { flex: 2 1 12rem; min-width: 0; }
.membership-row__role { flex: 1 1 auto; }
</style>
