import { createRouter, createWebHistory } from 'vue-router'
import { useSessionStore } from '@/stores/session'

const DashboardView = () => import('@/_UI/views/DashboardView.vue')
const LoginView = () => import('@/_UI/views/LoginView.vue')
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
  if (!to.meta.public && !localStorage.getItem('access_token')) return '/login'
  if (to.path === '/login' && localStorage.getItem('access_token')) return '/'
  if (to.meta.admin) {
    const session = useSessionStore()
    if (!session.user) await session.loadUser()
    if (!session.isAdmin) return '/'
  }
})

export default router
