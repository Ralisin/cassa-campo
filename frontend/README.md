# Cassa Campo Frontend

PWA Vue 3 in JavaScript, mobile-first, per la gestione economica del campo.
L'interfaccia utilizza PrimeVue con un preset Aura personalizzato.

## Avvio locale

```bash
cp .env.example .env
npm install
npm run dev
```

Il frontend comunica esclusivamente con il backend configurato tramite
`VITE_API_URL`.

## Deploy

Il sito statico su Render usa la cartella `frontend` del branch `main`.
Un push che modifica questa cartella avvia automaticamente una build. L'app
GitHub di Render deve avere accesso al repository `Ralisin/cassa-campo`.
