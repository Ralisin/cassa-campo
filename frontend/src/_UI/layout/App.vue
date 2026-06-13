<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useSessionStore } from '@/stores/session'

const session = useSessionStore()
const route = useRoute()
const router = useRouter()
const userMenu = ref()
const userMenuItems = computed(() => [
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
const userInitials = computed(() => {
  const name = session.user?.name?.trim()
  if (!name) return 'CC'
  return name.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()
})

const navItems = computed(() => [
  { label: 'Home', icon: 'pi pi-home', to: '/', key: 'home' },
  { label: 'Inserisci', icon: 'pi pi-plus', to: '/movimenti/nuovo', key: 'new' },
  { label: 'Movimenti', icon: 'pi pi-list', to: '/movimenti', key: 'movements' },
  { label: 'Rimborsi', icon: 'pi pi-replay', to: '/rimborsi', key: 'reimbursements' },
  { label: 'Riepilogo', icon: 'pi pi-chart-pie', to: '/riepilogo', key: 'summary' },
  ...(session.isAdmin ? [{ label: 'Utenti', icon: 'pi pi-users', to: '/utenti', key: 'users' }] : []),
])
const activeNavIndex = computed(() => Math.max(
  navItems.value.findIndex((item) => item.key === route.meta.nav),
  0,
))
const pageDirection = ref('forward')
const navMotion = ref('idle')
let navMotionTimer
const pageTransitionName = computed(() => `menu-page-${pageDirection.value}`)

watch(
  () => route.meta.nav,
  (next, previous) => {
    const nextIndex = navItems.value.findIndex((item) => item.key === next)
    const previousIndex = navItems.value.findIndex((item) => item.key === previous)
    if (nextIndex === previousIndex) pageDirection.value = 'fade'
    else pageDirection.value = nextIndex > previousIndex ? 'forward' : 'backward'
    navMotion.value = nextIndex > previousIndex ? 'right' : nextIndex < previousIndex ? 'left' : 'idle'
    window.clearTimeout(navMotionTimer)
    nextTick(() => {
      navMotionTimer = window.setTimeout(() => (navMotion.value = 'idle'), 560)
    })
  },
  { flush: 'sync' },
)

onMounted(async () => {
  if (session.authenticated && !session.user) {
    await session.loadUser().catch(() => {
      session.logout()
      router.push('/login')
    })
  }
})
</script>

<template>
  <div v-if="route.path !== '/login'" class="mx-auto min-h-screen max-w-3xl bg-[#f6f8f5] pb-24">
    <PToolbar class="sticky top-0 z-30 !rounded-none !border-x-0 !border-t-0 !bg-white/95 !px-4 backdrop-blur">
      <template #start>
        <PButton v-if="route.meta.back" icon="pi pi-arrow-left" text rounded aria-label="Indietro" @click="router.back()" />
        <PButton v-else icon="pi pi-bars" text rounded aria-label="Menu utente" @click="userMenu.toggle($event)" />
        <PMenu ref="userMenu" :model="userMenuItems" popup class="user-menu">
          <template #start>
            <div class="user-menu__profile">
              <PAvatar :label="userInitials" size="large" shape="circle" class="!bg-forest !font-black !text-white" />
              <div class="min-w-0">
                <p class="truncate text-sm font-black text-slate-900">{{ session.user?.name ?? 'Utente' }}</p>
                <p class="mt-0.5 truncate text-xs text-slate-500">{{ session.user?.email }}</p>
                <div class="mt-2 flex items-center gap-1.5">
                  <PTag :value="session.user?.role ?? 'utente'" severity="secondary" class="capitalize" />
                  <PTag v-if="session.user?.branch" :value="session.user.branch" severity="info" />
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
      </template>
      <template #center><h1 class="text-center text-base font-black text-slate-900">{{ route.meta.title }}</h1></template>
      <template #end><PButton icon="pi pi-bell" text rounded aria-label="Notifiche" /></template>
    </PToolbar>

    <div class="menu-page-shell px-4 py-5">
      <RouterView v-slot="{ Component, route: currentRoute }">
        <Transition :name="pageTransitionName" mode="out-in">
          <component :is="Component" :key="currentRoute.fullPath" />
        </Transition>
      </RouterView>
    </div>

    <nav
      class="mobile-tabbar"
      :class="`mobile-tabbar--moving-${navMotion}`"
      :style="{
        gridTemplateColumns: `repeat(${navItems.length}, minmax(0, 1fr))`,
        '--nav-count': navItems.length,
        '--active-offset': `${activeNavIndex * 100}%`,
      }"
    >
      <span class="mobile-tabbar__trail" aria-hidden="true" />
      <span class="mobile-tabbar__indicator" aria-hidden="true">
        <span class="mobile-tabbar__indicator-glow" />
        <span class="mobile-tabbar__indicator-surface" />
      </span>
      <RouterLink
        v-for="item in navItems"
        :key="item.key"
        :to="item.to"
        class="mobile-tabbar__item"
        :class="{ 'mobile-tabbar__item--active': route.meta.nav === item.key }"
      >
        <PButton
          :icon="item.icon"
          rounded
          :text="route.meta.nav !== item.key"
          :aria-label="item.label"
          class="mobile-tabbar__icon"
          :class="{ 'mobile-tabbar__icon--active': route.meta.nav === item.key }"
        />
        <span class="mobile-tabbar__label">{{ item.label }}</span>
      </RouterLink>
    </nav>
  </div>
  <RouterView v-else />
</template>
