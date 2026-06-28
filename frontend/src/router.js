import { createRouter, createWebHistory } from 'vue-router'
import { useSessionStore } from '@/stores/session'

const DashboardView = () => import('@/_UI/views/DashboardView.vue')
const LoginView = () => import('@/_UI/views/LoginView.vue')
const CassaSelectView = () => import('@/_UI/views/CassaSelectView.vue')
const MovementDetailView = () => import('@/_UI/views/MovementDetailView.vue')
const MovementFormView = () => import('@/_UI/views/MovementFormView.vue')
const MovementsView = () => import('@/_UI/views/MovementsView.vue')
const SummaryView = () => import('@/_UI/views/SummaryView.vue')
const UsersView = () => import('@/_UI/views/UsersView.vue')
const ReimbursementsView = () => import('@/_UI/views/ReimbursementsView.vue')

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: LoginView, meta: { public: true } },
    { path: '/seleziona-cassa', component: CassaSelectView, meta: { cassaSelect: true } },
    { path: '/', component: DashboardView, meta: { title: 'Campo 2026 · Reparto', nav: 'home' } },
    { path: '/movimenti', component: MovementsView, meta: { title: 'Movimenti', nav: 'movements' } },
    { path: '/movimenti/nuovo', component: MovementFormView, meta: { title: 'Nuovo movimento', nav: 'new', back: true } },
    { path: '/movimenti/:id', component: MovementDetailView, meta: { title: 'Dettaglio movimento', nav: 'movements', back: true } },
    { path: '/movimenti/:id/modifica', component: MovementFormView, meta: { title: 'Modifica movimento', nav: 'movements', back: true } },
    { path: '/riepilogo', component: SummaryView, meta: { title: 'Riepilogo campo', nav: 'summary' } },
    { path: '/utenti', component: UsersView, meta: { title: 'Gestione utenti', nav: 'users', admin: true } },
    { path: '/rimborsi', component: ReimbursementsView, meta: { title: 'Rimborsi', nav: 'reimbursements' } },
  ],
})

router.beforeEach(async (to) => {
  const token = localStorage.getItem('access_token')
  if (!to.meta.public && !token) return '/login'
  if (to.path === '/login' && token) return '/'
  if (!token) return true

  const session = useSessionStore()
  if (!session.user) {
    try {
      await session.loadUser()
    } catch {
      session.logout()
      return '/login'
    }
  }
  // The cassa picker is always reachable once authenticated.
  if (to.meta.cassaSelect) return true
  // Every other private page requires an active cassa.
  if (!to.meta.public && session.needsCassaSelection) return '/seleziona-cassa'
  if (to.meta.admin && !session.isAdmin) return '/'
  return true
})

export default router
