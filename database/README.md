# Cassa Campo Database

PostgreSQL 16 locale per lo sviluppo di Cassa Campo.

## Avvio

```bash
cp .env.example .env
docker compose up -d
```

Il database è disponibile su `localhost:5432`.

## Arresto

Mantieni i dati:

```bash
docker compose down
```

Elimina anche il volume e tutti i dati:

```bash
docker compose down --volumes
```

