<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'

import CassaManagementPanel from '@/components/CassaManagementPanel.vue'
import { useSessionStore } from '@/stores/session'

const session = useSessionStore()
const router = useRouter()

const ROLE_LABELS = { admin: 'Admin', cashier: 'Cassiere', user: 'Utente' }
const ROLE_SEVERITY = { admin: 'success', cashier: 'warn', user: 'secondary' }
const KIND_LABELS = { campo: 'Campo', anno: 'Anno' }

const memberships = computed(() => [...session.memberships].sort((a, b) => Number(a.is_closed) - Number(b.is_closed) || a.kind.localeCompare(b.kind) || b.year - a.year))

function roleLabel(role) {
  return ROLE_LABELS[role] ?? role
}

function unitInitials(unit) {
  return unit.replace(/[^A-Za-z]/g, '').slice(0, 2).toUpperCase() || unit.slice(0, 2)
}

function cassaLabel(membership) {
  return `${KIND_LABELS[membership.kind] ?? membership.kind} ${membership.year}`
}

function choose(cassaId) {
  if (session.setCassa(cassaId)) router.push('/')
}

function logout() {
  session.logout()
  router.push('/login')
}

onMounted(async () => {
  if (!session.user) await session.loadUser().catch(() => logout())
})
</script>

<template>
  <main class="cassa-select-page">
    <div class="cassa-select-shell">
      <header class="cassa-select-header">
        <PAvatar icon="pi pi-wallet" size="large" shape="circle" class="!bg-emerald-50 !text-forest" />
        <div>
          <p class="text-[11px] font-black uppercase tracking-[0.2em] text-emerald-600">Cassa Campo</p>
          <h1 class="mt-0.5 text-xl font-black text-slate-900">Scegli la cassa</h1>
          <p class="mt-0.5 text-sm text-slate-500">
            {{ session.user?.name }}, seleziona su quale cassa vuoi operare.
          </p>
        </div>
      </header>

      <div v-if="memberships.length" class="space-y-2">
        <button
          v-for="membership in memberships"
          :key="membership.cassa_id"
          type="button"
          class="cassa-option"
          :class="{ 'cassa-option--active': membership.cassa_id === session.activeCassaId }"
          @click="choose(membership.cassa_id)"
        >
          <PAvatar :label="unitInitials(membership.unit)" shape="circle" class="cassa-option__avatar" />
          <span class="min-w-0 flex-1 text-left">
            <span class="block truncate text-sm font-black text-slate-900">{{ membership.unit }}</span>
            <span class="block truncate text-xs text-slate-500">{{ membership.group_name }} · {{ cassaLabel(membership) }}</span>
          </span>
          <PTag v-if="membership.is_closed" value="Chiusa" severity="secondary" />
          <PTag :value="roleLabel(membership.role)" :severity="ROLE_SEVERITY[membership.role]" />
          <i class="pi pi-chevron-right text-sm text-slate-400" />
        </button>
      </div>

      <PCard v-else class="cassa-select-empty">
        <template #content>
          <div class="flex flex-col items-center gap-2 text-center">
            <PAvatar icon="pi pi-inbox" size="large" shape="circle" class="!bg-slate-100 !text-slate-400" />
            <p class="text-sm font-black text-slate-900">Nessuna cassa assegnata</p>
            <p class="text-xs text-slate-500">
              Il tuo profilo non è ancora collegato a nessuna cassa. Contatta un responsabile del gruppo.
            </p>
          </div>
        </template>
      </PCard>

      <PButton
        label="Esci"
        icon="pi pi-sign-out"
        text
        class="cassa-select-logout"
        @click="logout"
      />

      <CassaManagementPanel v-if="session.canManageCasse" />
    </div>
  </main>
</template>

<style scoped>
.cassa-select-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem 1rem;
  background: #f6f8f5;
}
.cassa-select-shell {
  width: 100%;
  max-width: 28rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}
.cassa-select-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.cassa-option {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  padding: 0.85rem 1rem;
  border-radius: 1rem;
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, 0.06);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  transition: transform 0.12s ease, border-color 0.12s ease, box-shadow 0.12s ease;
}
.cassa-option:hover {
  transform: translateY(-1px);
  border-color: rgba(52, 125, 89, 0.4);
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.08);
}
.cassa-option--active {
  border-color: var(--p-primary-400, #509c74);
}
.cassa-option__avatar {
  background: #edf7f1 !important;
  color: var(--p-primary-700, #224f3b) !important;
  font-weight: 900 !important;
}
.cassa-select-logout {
  align-self: center;
}
</style>
