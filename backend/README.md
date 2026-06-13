# Cassa Campo Backend

API FastAPI per autenticazione, movimenti, rimborsi, dashboard, impostazioni ed
export Excel.

## Avvio locale

Il database di sviluppo gira su PostgreSQL 16 tramite Docker nella cartella
sorella `database`:

```bash
cd ../database
cp .env.example .env
docker compose up -d
cd ../backend
```

Poi prepara e avvia il backend:

```bash
cp .env.example .env
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

Documentazione API: `http://localhost:8000/docs`.

Per fermare PostgreSQL, dalla cartella `database`:

```bash
cd ../database
docker compose down
```

I dati restano nel volume Docker `postgres_data`. Per eliminarli completamente:

```bash
docker compose down --volumes
```

Per creare il primo admin:

```bash
python -m app.create_admin admin@example.it "Nome Admin" "password-sicura" "Gruppo"
```
