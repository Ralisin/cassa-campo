import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { api } from '@/api'
export const useSessionStore = defineStore('session', () => {
  const user = ref(null)
  const token = ref(localStorage.getItem('access_token'))
  const authenticated = computed(() => Boolean(token.value))
  const isAdmin = computed(() => user.value?.role === 'admin')

  async function login(email, password) {
    const result = await api.post('/auth/login', { email, password })
    token.value = result.access_token
    localStorage.setItem('access_token', result.access_token)
    await loadUser()
  }

  async function loadUser() {
    if (!token.value) return
    user.value = await api.get('/auth/me')
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('access_token')
  }

  return { user, authenticated, isAdmin, login, loadUser, logout }
})
