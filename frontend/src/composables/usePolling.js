import { onMounted, onUnmounted } from 'vue'

export function usePolling(callback, interval = 7000) {
  let timer
  let running = false

  async function refresh() {
    if (running || document.hidden) return
    running = true
    try {
      await callback()
    } catch {
      // Keep the currently displayed data if a background refresh fails.
    } finally {
      running = false
    }
  }

  function handleVisibilityChange() {
    if (!document.hidden) void refresh()
  }

  onMounted(() => {
    timer = window.setInterval(() => void refresh(), interval)
    document.addEventListener('visibilitychange', handleVisibilityChange)
  })

  onUnmounted(() => {
    window.clearInterval(timer)
    document.removeEventListener('visibilitychange', handleVisibilityChange)
  })
}
