self.addEventListener('push', (event) => {
  let payload = {}
  try {
    payload = event.data ? event.data.json() : {}
  } catch {
    payload = { body: event.data?.text() }
  }

  const title = payload.title || 'Cassa Campo'
  const options = {
    body: payload.body || 'Hai una nuova notifica',
    icon: '/pwa-192x192.png',
    badge: '/favicon-32x32.png',
    tag: payload.tag || payload.data?.notification_id || 'cassa-campo',
    data: payload.data || { url: payload.url || '/' },
  }

  event.waitUntil(self.registration.showNotification(title, options))
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const url = event.notification.data?.url || '/'
  const targetUrl = new URL(url, self.location.origin).href

  event.waitUntil((async () => {
    const windows = await self.clients.matchAll({ type: 'window', includeUncontrolled: true })
    const existing = windows.find((client) => client.url.startsWith(self.location.origin))
    if (existing) {
      await existing.focus()
      existing.postMessage({ type: 'OPEN_URL', url })
      return
    }
    await self.clients.openWindow(targetUrl)
  })())
})
