<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAppChrome } from '@/composables/useAppChrome'
import { useSessionStore } from '@/stores/session'

defineProps({ collapsed: { type: Boolean, default: false } })
defineEmits(['toggle'])

const session = useSessionStore()
const route = useRoute()
const router = useRouter()
const { pendingReimbursementCount, reimbursementCountLabel } = useAppChrome()
const userMenu = ref()

const ROLE_LABELS = { admin: 'Admin', cashier: 'Cassiere', user: 'Utente' }

const navItems = computed(() => [
  { label: 'Dashboard', icon: 'pi pi-th-large', to: '/', key: 'home' },
  { label: 'Movimenti', icon: 'pi pi-list', to: '/movimenti', key: 'movements' },
  { label: 'Rimborsi', icon: 'pi pi-replay', to: '/rimborsi', key: 'reimbursements', badge: true },
  { label: 'Riepilogo', icon: 'pi pi-chart-pie', to: '/riepilogo', key: 'summary' },
  ...(session.isOperator ? [{ label: 'Impostazioni', icon: 'pi pi-sliders-h', to: '/impostazioni', key: 'settings' }] : []),
  ...(session.isAdmin ? [{ label: 'Utenti', icon: 'pi pi-users', to: '/utenti', key: 'users' }] : []),
])

const userInitials = computed(() => {
  const name = session.user?.name?.trim()
  if (!name) return 'CC'
  return name.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()
})

const userMenuItems = computed(() => [
  ...(session.memberships.length > 1
    ? [{ label: 'Cambia cassa', icon: 'pi pi-sync', command: () => router.push('/seleziona-cassa') }]
    : []),
  { separator: true },
  {
    label: 'Esci',
    icon: 'pi pi-sign-out',
    command: () => {
      session.logout()
      router.push('/login')
    },
  },
])
</script>

<template>
  <div class="dk-side">
    <div class="dk-side__brand">
      <img src="/icon.svg" alt="" class="dk-side__logo" />
      <div v-if="!collapsed" class="dk-side__brand-text">
        <span class="dk-side__brand-name">Cassa Campo</span>
        <span class="dk-side__brand-sub">Gestione economica</span>
      </div>
      <button type="button" class="dk-side__collapse" :aria-label="collapsed ? 'Espandi menu' : 'Comprimi menu'" @click="$emit('toggle')">
        <i :class="collapsed ? 'pi pi-angle-double-right' : 'pi pi-angle-double-left'" />
      </button>
    </div>

    <nav class="dk-side__nav">
      <RouterLink
        v-for="item in navItems"
        :key="item.key"
        v-tooltip.right="collapsed ? item.label : null"
        :to="item.to"
        class="dk-nav-item"
        :class="{ 'dk-nav-item--active': route.meta.nav === item.key }"
      >
        <span class="dk-nav-item__icon"><i :class="item.icon" /></span>
        <span v-if="!collapsed" class="dk-nav-item__label">{{ item.label }}</span>
        <span
          v-if="item.badge && pendingReimbursementCount"
          class="dk-nav-item__badge"
          :class="{ 'dk-nav-item__badge--dot': collapsed }"
        >{{ collapsed ? '' : reimbursementCountLabel }}</span>
      </RouterLink>
    </nav>

    <div class="dk-side__footer">
      <button type="button" class="dk-side__user" :aria-label="session.user?.name" @click="userMenu.toggle($event)">
        <PAvatar :label="userInitials" shape="circle" class="dk-side__avatar" />
        <span v-if="!collapsed" class="dk-side__user-info">
          <span class="dk-side__user-name">{{ session.user?.name ?? 'Utente' }}</span>
          <span v-if="session.activeCassa" class="dk-side__user-meta">
            {{ session.activeCassa.unit }} · {{ ROLE_LABELS[session.activeCassa.role] ?? session.activeCassa.role }}
          </span>
        </span>
        <i v-if="!collapsed" class="pi pi-ellipsis-v dk-side__user-caret" />
      </button>
      <PMenu ref="userMenu" :model="userMenuItems" popup class="user-menu">
        <template #start>
          <div class="user-menu__profile">
            <PAvatar :label="userInitials" size="large" shape="circle" class="!bg-forest !font-black !text-white" />
            <div class="min-w-0">
              <p class="truncate text-sm font-black text-slate-900">{{ session.user?.name ?? 'Utente' }}</p>
              <p class="mt-0.5 truncate text-xs text-slate-500">{{ session.user?.email }}</p>
              <div v-if="session.activeCassa" class="mt-2 flex flex-wrap items-center gap-1.5">
                <PTag :value="ROLE_LABELS[session.activeCassa.role] ?? session.activeCassa.role" severity="success" />
                <PTag :value="session.activeCassa.unit" severity="info" />
                <PTag :value="session.activeCassa.group_name" severity="secondary" />
              </div>
            </div>
          </div>
        </template>
        <template #item="{ item, props }">
          <a v-bind="props.action" class="user-menu__logout">
            <i :class="item.icon" /><span>{{ item.label }}</span>
          </a>
        </template>
      </PMenu>
    </div>
  </div>
</template>
