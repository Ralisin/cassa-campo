<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { api } from '@/api'
import { useSessionStore } from '@/stores/session'

const session = useSessionStore()
const router = useRouter()
const users = ref([])
const dialogVisible = ref(false)
const saving = ref(false)
const submitted = ref(false)
const error = ref('')
const editingId = ref(null)
const branches = ['L/C', 'E/G', 'R/S', 'CoCa', 'Gruppo']
const roles = [
  { label: 'Utente', value: 'user' },
  { label: 'Admin', value: 'admin' },
]
const form = reactive({
  name: '',
  email: '',
  role: 'user',
  branch: 'E/G',
  password: '',
})
const editing = computed(() => Boolean(editingId.value))
const nameInvalid = computed(() => submitted.value && !form.name.trim())
const emailInvalid = computed(() => submitted.value && !form.email.trim())
const passwordInvalid = computed(
  () => submitted.value && ((!editing.value || form.password) && form.password.length < 8),
)

async function loadUsers() {
  users.value = await api.get('/users')
}

function openCreate() {
  editingId.value = null
  Object.assign(form, { name: '', email: '', role: 'user', branch: 'E/G', password: '' })
  submitted.value = false
  error.value = ''
  dialogVisible.value = true
}

function openEdit(user) {
  editingId.value = user.id
  Object.assign(form, {
    name: user.name,
    email: user.email,
    role: user.role,
    branch: user.branch,
    password: '',
  })
  submitted.value = false
  error.value = ''
  dialogVisible.value = true
}

async function save() {
  submitted.value = true
  error.value = ''
  if (nameInvalid.value || emailInvalid.value || passwordInvalid.value) return
  saving.value = true
  try {
    const payload = { ...form }
    if (editing.value && !payload.password) delete payload.password
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

function initials(name) {
  return name.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()
}

onMounted(loadUsers)
</script>

<template>
  <main class="space-y-4">
    <PCard class="users-header-card">
      <template #content>
        <div class="flex items-center gap-3">
          <PAvatar icon="pi pi-users" size="large" shape="circle" class="!bg-emerald-50 !text-forest" />
          <div class="min-w-0 flex-1">
            <h2 class="text-base font-black text-slate-900">Persone abilitate</h2>
            <p class="mt-0.5 text-xs text-slate-500">{{ users.length }} profili registrati</p>
          </div>
          <PButton icon="pi pi-user-plus" rounded aria-label="Registra persona" class="primary-cta !h-11 !min-h-0 !w-11 !min-w-11 !p-0" @click="openCreate" />
        </div>
      </template>
    </PCard>

    <PDataView :value="users" class="movement-data-view">
      <template #list="{ items }">
        <div class="space-y-2">
          <PCard v-for="user in items" :key="user.id" class="user-list-card cursor-pointer" @click="openEdit(user)">
            <template #content>
              <div class="flex items-center gap-3">
                <PAvatar :label="initials(user.name)" size="large" shape="circle" class="!bg-slate-100 !font-black !text-forest" />
                <div class="min-w-0 flex-1">
                  <div class="flex items-center gap-2">
                    <p class="truncate text-sm font-black text-slate-900">{{ user.name }}</p>
                    <PTag v-if="user.id === session.user?.id" value="Tu" severity="secondary" />
                  </div>
                  <p class="mt-0.5 truncate text-xs text-slate-500">{{ user.email }}</p>
                  <div class="mt-2 flex gap-1.5">
                    <PTag :value="user.role" :severity="user.role === 'admin' ? 'success' : 'secondary'" class="capitalize" />
                    <PTag :value="user.branch" severity="info" />
                  </div>
                </div>
                <i class="pi pi-pencil text-sm text-slate-400" />
              </div>
            </template>
          </PCard>
        </div>
      </template>
    </PDataView>

    <PDialog v-model:visible="dialogVisible" modal :header="editing ? 'Modifica persona' : 'Registra persona'" class="summary-dialog user-dialog w-[calc(100vw-2rem)] max-w-md">
      <form class="summary-dialog__form" novalidate @submit.prevent="save">
        <p class="summary-dialog__intro">
          <i :class="editing ? 'pi pi-user-edit' : 'pi pi-user-plus'" />
          {{ editing ? 'Aggiorna i dati e i permessi della persona.' : 'Crea un accesso e assegna ruolo e branca.' }}
        </p>
        <div class="summary-dialog__field">
          <label for="user-name">Nome <span class="required-mark">*</span></label>
          <PInputText id="user-name" v-model="form.name" :invalid="nameInvalid" fluid />
          <small v-if="nameInvalid" class="field-error">Il nome è obbligatorio.</small>
        </div>
        <div class="summary-dialog__field">
          <label for="user-email">Email <span class="required-mark">*</span></label>
          <PInputText id="user-email" v-model="form.email" type="email" :invalid="emailInvalid" fluid />
          <small v-if="emailInvalid" class="field-error">L’email è obbligatoria.</small>
        </div>
        <div class="user-dialog__selects">
          <div class="summary-dialog__field"><label for="user-role">Ruolo</label><PSelect id="user-role" v-model="form.role" :options="roles" option-label="label" option-value="value" fluid /></div>
          <div class="summary-dialog__field"><label for="user-branch">Branca</label><PSelect id="user-branch" v-model="form.branch" :options="branches" fluid /></div>
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
  </main>
</template>
