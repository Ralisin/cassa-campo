import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { api } from '@/api'

export const useSessionStore = defineStore('session', () => {
  const user = ref(null)
  const token = ref(localStorage.getItem('access_token'))
  const activeCassaId = ref(localStorage.getItem('active_cassa_id'))

  const authenticated = computed(() => Boolean(token.value))
  const memberships = computed(() => user.value?.memberships ?? [])
  const activeMembership = computed(
    () => memberships.value.find((item) => item.cassa_id === activeCassaId.value) ?? null,
  )
  // The active cassa context: { cassa_id, unit, role, group_id, group_slug, group_name }.
  const activeCassa = computed(() => activeMembership.value)
  const role = computed(() => activeMembership.value?.role ?? null)
  const isAdmin = computed(() => role.value === 'admin')
  const isOperator = computed(() => ['admin', 'cashier'].includes(role.value))
  const hasMemberships = computed(() => memberships.value.length > 0)
  // True once authenticated and the profile is loaded but no cassa is active yet
  // (more than one cassa to pick, or none assigned at all).
  const needsCassaSelection = computed(
    () => authenticated.value && Boolean(user.value) && !activeMembership.value,
  )

  function persistCassa(cassaId) {
    activeCassaId.value = cassaId
    if (cassaId) localStorage.setItem('active_cassa_id', cassaId)
    else localStorage.removeItem('active_cassa_id')
  }

  function setCassa(cassaId) {
    if (!memberships.value.some((item) => item.cassa_id === cassaId)) return false
    persistCassa(cassaId)
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
    // Drop a stale selection and auto-select when there is exactly one cassa.
    if (!activeMembership.value) {
      persistCassa(memberships.value.length === 1 ? memberships.value[0].cassa_id : null)
    }
  }

  function logout() {
    token.value = null
    user.value = null
    persistCassa(null)
    localStorage.removeItem('access_token')
  }

  return {
    user,
    token,
    authenticated,
    memberships,
    activeMembership,
    activeCassa,
    activeCassaId,
    role,
    isAdmin,
    isOperator,
    hasMemberships,
    needsCassaSelection,
    login,
    loadUser,
    logout,
    setCassa,
  }
})
