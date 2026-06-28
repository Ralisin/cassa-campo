import { onMounted, onUnmounted, ref } from 'vue'

// Single source of truth for the desktop breakpoint. The desktop "gestionale"
// shell takes over at >= 1024px; below that the existing mobile PWA shell stays.
const DESKTOP_QUERY = '(min-width: 1024px)'

const query = typeof window !== 'undefined' && window.matchMedia
  ? window.matchMedia(DESKTOP_QUERY)
  : null

// Module-level reactive state so every consumer shares the same value and we
// register a single matchMedia listener.
const isDesktop = ref(query ? query.matches : false)
let listeners = 0

function handleChange(event) {
  isDesktop.value = event.matches
}

export function useViewport() {
  onMounted(() => {
    if (!query) return
    if (listeners === 0) query.addEventListener('change', handleChange)
    listeners += 1
    // Re-sync in case the media state changed before this component mounted.
    isDesktop.value = query.matches
  })

  onUnmounted(() => {
    if (!query) return
    listeners -= 1
    if (listeners === 0) query.removeEventListener('change', handleChange)
  })

  return { isDesktop }
}
