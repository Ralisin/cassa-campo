<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import CassaManagementPanel from '@/components/CassaManagementPanel.vue'
import { useSessionStore } from '@/stores/session'

const session = useSessionStore()
const router = useRouter()
const managementExpanded = ref(false)

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
  <main class="dk-pick">
    <div class="dk-pick__inner">
      <header class="dk-pick__header">
        <img src="/icon.svg" alt="" class="dk-pick__logo" />
        <div class="min-w-0 flex-1">
          <p class="dk-login__brand-sub" style="color: var(--dk-moss)">Cassa Campo</p>
          <h1 class="dk-pick__title">Scegli la cassa</h1>
          <p class="dk-pick__sub">{{ session.user?.name }}, seleziona su quale cassa vuoi operare.</p>
        </div>
        <PButton label="Esci" icon="pi pi-sign-out" text @click="logout" />
      </header>

      <div v-if="memberships.length" class="dk-pick__grid">
        <button
          v-for="membership in memberships"
          :key="membership.cassa_id"
          type="button"
          class="dk-pick__card"
          @click="choose(membership.cassa_id)"
        >
          <div class="dk-pick__card-top">
            <PAvatar :label="unitInitials(membership.unit)" size="large" shape="circle" class="dk-pick__unit-av" />
            <div class="flex flex-wrap justify-end gap-1.5">
              <PTag v-if="membership.is_closed" value="Chiusa" severity="secondary" />
              <PTag :value="roleLabel(membership.role)" :severity="ROLE_SEVERITY[membership.role]" />
            </div>
          </div>
          <p class="dk-pick__card-unit">{{ membership.unit }}</p>
          <p class="dk-pick__card-group">{{ membership.group_name }} · {{ cassaLabel(membership) }}</p>
          <p class="mt-3 flex items-center gap-1.5 text-sm font-bold text-emerald-700">
            Entra <i class="pi pi-arrow-right text-xs" />
          </p>
        </button>
      </div>

      <div v-else class="dk-card" style="max-width: 28rem; margin: 0 auto; text-align: center;">
        <PAvatar icon="pi pi-inbox" size="large" shape="circle" class="!bg-slate-100 !text-slate-400" />
        <p class="mt-3 text-base font-black">Nessuna cassa assegnata</p>
        <p class="mt-1 text-sm text-slate-500">
          Il tuo profilo non è ancora collegato a nessuna cassa. Contatta un responsabile del gruppo.
        </p>
      </div>

      <section v-if="session.canManageCasse" class="dk-card">
        <div class="dk-card__head">
          <div>
            <h2 class="dk-card__title"><i class="pi pi-wallet dk-card__title-icon" /> Gestione casse</h2>
            <p class="dk-card__subtitle">Crea o chiudi casse del gruppo quando serve.</p>
          </div>
          <PButton
            :label="managementExpanded ? 'Nascondi' : 'Apri gestione'"
            :icon="managementExpanded ? 'pi pi-chevron-up' : 'pi pi-chevron-down'"
            outlined
            @click="managementExpanded = !managementExpanded"
          />
        </div>
        <Transition name="menu-page-fade">
          <CassaManagementPanel v-if="managementExpanded" />
        </Transition>
      </section>
    </div>
  </main>
</template>
