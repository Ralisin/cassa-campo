import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { api } from '@/api'

function storedSystemCassa() {
  try {
    return JSON.parse(localStorage.getItem('system_active_cassa') || 'null')
  } catch {
    localStorage.removeItem('system_active_cassa')
    return null
  }
}

export const useSessionStore = defineStore('session', () => {
  const user = ref(null)
  const token = ref(localStorage.getItem('access_token'))
  const activeCassaId = ref(localStorage.getItem('active_cassa_id'))
  const systemCassa = ref(storedSystemCassa())

  const authenticated = computed(() => Boolean(token.value))
  const isSystemAdmin = computed(() => Boolean(user.value?.is_system_admin))
  const memberships = computed(() => user.value?.memberships ?? [])
  const activeMembership = computed(
    () => memberships.value.find((item) => item.cassa_id === activeCassaId.value) ?? null,
  )
  // The active cassa context includes lifecycle metadata: kind, year, status and is_closed.
  const activeCassa = computed(() => activeMembership.value ?? (isSystemAdmin.value ? systemCassa.value : null))
  const role = computed(() => activeCassa.value?.role ?? null)
  const isAdmin = computed(() => isSystemAdmin.value || role.value === 'admin')
  const cassaClosed = computed(() => Boolean(activeCassa.value?.is_closed || activeCassa.value?.status === 'chiusa'))
  const isOperator = computed(() => (isSystemAdmin.value || ['admin', 'cashier'].includes(role.value)) && !cassaClosed.value)
  const canManageCasse = computed(
    () => isSystemAdmin.value || ['admin', 'cashier'].includes(role.value) || memberships.value.some((item) => ['admin', 'cashier'].includes(item.role)),
  )
  const cassaManagementContextId = computed(() => {
    if (isSystemAdmin.value && activeCassaId.value) return activeCassaId.value
    if (activeMembership.value && ['admin', 'cashier'].includes(activeMembership.value.role)) {
      return activeMembership.value.cassa_id
    }
    return memberships.value.find((item) => ['admin', 'cashier'].includes(item.role))?.cassa_id ?? null
  })
  const hasMemberships = computed(() => memberships.value.length > 0)
  // True once authenticated and the profile is loaded but no cassa is active yet
  // (more than one cassa to pick, or none assigned at all).
  const needsCassaSelection = computed(
    () => authenticated.value && Boolean(user.value) && !isSystemAdmin.value && !activeMembership.value,
  )
  const needsSystemCassaSelection = computed(
    () => authenticated.value && Boolean(user.value) && isSystemAdmin.value && !activeCassa.value,
  )

  function persistCassa(cassaId) {
    activeCassaId.value = cassaId
    if (cassaId) localStorage.setItem('active_cassa_id', cassaId)
    else localStorage.removeItem('active_cassa_id')
  }

  function persistSystemCassa(cassa) {
    systemCassa.value = cassa
    if (cassa) {
      localStorage.setItem('system_active_cassa', JSON.stringify(cassa))
      persistCassa(cassa.cassa_id)
    } else {
      localStorage.removeItem('system_active_cassa')
      persistCassa(null)
    }
  }

  function setCassa(cassaId) {
    if (!memberships.value.some((item) => item.cassa_id === cassaId)) return false
    persistCassa(cassaId)
    return true
  }

  function setSystemCassa(cassa) {
    if (!isSystemAdmin.value) return false
    if (!cassa) {
      persistSystemCassa(null)
      return true
    }
    persistSystemCassa({ ...cassa, role: 'admin' })
    return true
  }

  async function login(email, password) {
    const result = await api.post('/auth/login', { email, password })
    token.value = result.access_token
    localStorage.setItem('access_token', result.access_token)
    await loadUser()
  }

  async function loadUser() {
    if (!token.value) return
    user.value = await api.get('/auth/me')
    if (!isSystemAdmin.value) persistSystemCassa(null)
    // Drop a stale selection and auto-select when there is exactly one cassa.
    if (!isSystemAdmin.value && !activeMembership.value) {
      persistCassa(memberships.value.length === 1 ? memberships.value[0].cassa_id : null)
    }
  }

  function logout() {
    token.value = null
    user.value = null
    systemCassa.value = null
    persistCassa(null)
    localStorage.removeItem('access_token')
    localStorage.removeItem('system_active_cassa')
  }

  return {
    user,
    token,
    authenticated,
    isSystemAdmin,
    memberships,
    activeMembership,
    activeCassa,
    activeCassaId,
    role,
    isAdmin,
    isOperator,
    cassaClosed,
    canManageCasse,
    cassaManagementContextId,
    hasMemberships,
    needsCassaSelection,
    needsSystemCassaSelection,
    login,
    loadUser,
    logout,
    setCassa,
    setSystemCassa,
  }
})
