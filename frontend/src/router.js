import { createRouter, createWebHistory } from 'vue-router'
import { useSessionStore } from '@/stores/session'

// Mobile views (existing PWA experience) — rendered through the default
// router-view inside MobileShell.
const DashboardView = () => import('@/_UI/views/DashboardView.vue')
const LoginView = () => import('@/_UI/views/LoginView.vue')
const ResetPasswordView = () => import('@/_UI/views/ResetPasswordView.vue')
const CassaSelectView = () => import('@/_UI/views/CassaSelectView.vue')
const MovementDetailView = () => import('@/_UI/views/MovementDetailView.vue')
const MovementFormView = () => import('@/_UI/views/MovementFormView.vue')
const MovementsView = () => import('@/_UI/views/MovementsView.vue')
const SummaryView = () => import('@/_UI/views/SummaryView.vue')
const UsersView = () => import('@/_UI/views/UsersView.vue')
const ReimbursementsView = () => import('@/_UI/views/ReimbursementsView.vue')
const AuditView = () => import('@/_UI/views/AuditView.vue')
const SystemAdminView = () => import('@/desktop/views/SystemAdminView.vue')

// Desktop "gestionale" views — rendered through the `desktop` named router-view
// inside DesktopShell. They reuse the same stores/API as the mobile views.
const DDashboardView = () => import('@/desktop/views/DashboardView.vue')
const DLoginView = () => import('@/desktop/views/LoginView.vue')
const DCassaSelectView = () => import('@/desktop/views/CassaSelectView.vue')
const DMovementDetailView = () => import('@/desktop/views/MovementDetailView.vue')
const DMovementFormView = () => import('@/desktop/views/MovementFormView.vue')
const DMovementsView = () => import('@/desktop/views/MovementsView.vue')
const DSummaryView = () => import('@/desktop/views/SummaryView.vue')
const DSettingsView = () => import('@/desktop/views/SettingsView.vue')
const DUsersView = () => import('@/desktop/views/UsersView.vue')
const DReimbursementsView = () => import('@/desktop/views/ReimbursementsView.vue')
const DSystemAdminView = () => import('@/desktop/views/SystemAdminView.vue')

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', components: { default: LoginView, desktop: DLoginView }, meta: { public: true } },
    { path: '/reset-password', components: { default: ResetPasswordView, desktop: ResetPasswordView }, meta: { public: true } },
    { path: '/seleziona-cassa', components: { default: CassaSelectView, desktop: DCassaSelectView }, meta: { cassaSelect: true } },
    { path: '/system', components: { default: SystemAdminView, desktop: DSystemAdminView }, meta: { title: 'Sistema', nav: 'system', system: true } },
    { path: '/', components: { default: DashboardView, desktop: DDashboardView }, meta: { title: 'Campo 2026 · Reparto', nav: 'home' } },
    { path: '/movimenti', components: { default: MovementsView, desktop: DMovementsView }, meta: { title: 'Movimenti', nav: 'movements' } },
    { path: '/movimenti/nuovo', components: { default: MovementFormView, desktop: DMovementFormView }, meta: { title: 'Nuovo movimento', nav: 'new', back: true, writable: true } },
    { path: '/movimenti/:id', components: { default: MovementDetailView, desktop: DMovementDetailView }, meta: { title: 'Dettaglio movimento', nav: 'movements', back: true } },
    { path: '/movimenti/:id/modifica', components: { default: MovementFormView, desktop: DMovementFormView }, meta: { title: 'Modifica movimento', nav: 'movements', back: true, writable: true } },
    { path: '/riepilogo', components: { default: SummaryView, desktop: DSummaryView }, meta: { title: 'Riepilogo campo', nav: 'summary' } },
    { path: '/impostazioni', components: { default: SummaryView, desktop: DSettingsView }, meta: { title: 'Impostazioni', nav: 'settings', operator: true } },
    { path: '/utenti', components: { default: UsersView, desktop: DUsersView }, meta: { title: 'Gestione utenti', nav: 'users', admin: true } },
    { path: '/rimborsi', components: { default: ReimbursementsView, desktop: DReimbursementsView }, meta: { title: 'Rimborsi', nav: 'reimbursements' } },
    { path: '/audit', components: { default: AuditView, desktop: AuditView }, meta: { title: 'Audit', nav: 'audit', operator: true } },
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
  if (to.path === '/login' && session.isSystemAdmin) return '/system'
  // The cassa picker is always reachable once authenticated.
  if (to.meta.cassaSelect) return true
  if (to.meta.system && !session.isSystemAdmin) return '/'
  if (session.isSystemAdmin && !to.meta.public && !to.meta.system && session.needsSystemCassaSelection) return '/system'
  // Every other private page requires an active cassa.
  if (!to.meta.public && session.needsCassaSelection) return '/seleziona-cassa'
  if (to.meta.writable && session.cassaClosed) return '/'
  if (to.meta.admin && !session.isAdmin) return '/'
  if (to.meta.operator && !session.isOperator) return '/'
  return true
})

export default router
