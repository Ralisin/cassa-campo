# Cassa Campo - Documento di Architettura

## Obiettivo

Realizzare una webapp mobile-first per la gestione economica del Campo Estivo di Reparto.

L'applicazione deve essere:

* semplice e veloce da utilizzare da smartphone
* installabile come PWA
* condivisa tra più utenti
* accessibile tramite autenticazione
* in grado di esportare dati in Excel
* gratuita da mantenere
* facilmente estendibile negli anni

---

# Stack Tecnologico

## Frontend

Tecnologie:

* Vue 3
* JavaScript
* Vite
* Pinia
* Vue Router
* PrimeVue
* TailwindCSS
* PWA

Hosting:

* Render Static Site (Free)

Responsabilità:

* interfaccia utente
* gestione sessione
* visualizzazione dati
* chiamate API al backend

Il frontend non comunica mai direttamente con Supabase.

---

## Backend

Tecnologie:

* Python 3.12
* FastAPI
* Uvicorn
* SQLAlchemy
* Alembic
* Pydantic
* OpenPyXL

Hosting:

* Render Web Service (Free)

Responsabilità:

* autenticazione
* autorizzazione
* CRUD completo
* dashboard
* reportistica
* esportazione Excel
* accesso database

Tutta la logica applicativa risiede nel backend.

---

## Database

Tecnologie:

* Supabase PostgreSQL

Utilizzo:

* database relazionale
* persistenza dati

Supabase viene utilizzato esclusivamente come database PostgreSQL.

Non verranno utilizzati:

* Supabase Auth
* Supabase Realtime
* Supabase Storage (inizialmente)

---

# Architettura

```text
Vue 3 PWA
      │
      ▼
 FastAPI Backend
      │
      ▼
Supabase PostgreSQL
```

Tutte le richieste passano dal backend.

---

# Autenticazione

## Login

Endpoint:

POST /auth/login

Input:

```json
{
  "email": "utente@email.it",
  "password": "password"
}
```

Output:

```json
{
  "access_token": "...",
  "token_type": "bearer"
}
```

---

## Me

Endpoint:

GET /auth/me

Restituisce:

* id utente
* nome
* ruolo
* branca di appartenenza

Ogni profilo deve essere associato obbligatoriamente a una branca.
I profili preesistenti senza branca vengono migrati sulla branca `E/G`.

---

# Ruoli

## Admin

Permessi:

* visualizzare lo stato della cassa
* visualizzare la lista globale dei movimenti e il dettaglio di ogni movimento
* visualizzare il riepilogo completo
* creare movimenti
* modificare i propri movimenti
* modificare i movimenti inseriti da altri utenti
* eliminare movimenti
* esportare Excel
* impostare il saldo iniziale dei contanti e della carta
* gestire gli utenti: registrarli, modificarne nome, email, ruolo, branca e password
* visualizzare e filtrare tutti i rimborsi
* segnare un rimborso come completato o riportarlo allo stato da rimborsare

La gestione utenti è disponibile esclusivamente agli admin. Il sistema non
permette di rimuovere il ruolo all'ultimo admin rimasto.

---

## Utente

Permessi:

* visualizzare lo stato della cassa
* visualizzare la lista globale dei movimenti e il dettaglio di ogni movimento
* visualizzare il riepilogo completo
* creare movimenti
* modificare esclusivamente i propri movimenti
* inserire movimenti esclusivamente per la branca associata al proprio profilo
* visualizzare e filtrare i propri rimborsi e il totale ancora dovuto

Non può:

* modificare movimenti inseriti da altri utenti
* eliminare movimenti
* esportare Excel
* modificare i saldi iniziali

---

# Dashboard

## Dati mostrati

### Budget

* Spesa Massima
* Spesa Eseguita
* Budget Residuo

### Saldi

* Contanti
* Banca

### Attività recente

* movimenti con data operazione uguale al giorno corrente
* autore che ha inserito ciascun movimento
* collegamento alla lista completa quando non sono presenti movimenti nel giorno corrente

---

# Movimenti

La lista globale può essere filtrata per tipo, metodo di pagamento e autore
del movimento. Il pannello filtri è collassabile. I movimenti sono raggruppati
per data e ogni gruppo può essere espanso o collassato cliccando sulla relativa
data.

## Campi

### Tipo

* Entrata
* Uscita

### Metodo pagamento

* Contanti
* Carta

### Rimborso necessario

Indica che la spesa è stata anticipata personalmente e deve essere rimborsata
a chi ha effettuato l'acquisto.

Nel database questa informazione non è salvata come flag nel movimento. La
presenza di una riga collegata nella tabella `movement_reimbursements` indica
che il movimento necessita di rimborso.

Vincoli:

* può essere impostato solo per movimenti di tipo `Uscita`
* quando viene impostato, il frontend seleziona automaticamente il metodo di
  pagamento `Contanti` e non permette di modificarlo
* il backend valida sempre che un movimento con rimborso necessario sia
  un'uscita in contanti, anche se la richiesta non proviene dal frontend

La relazione traccia anche se il rimborso è stato completato, quando è stato
completato e quale admin lo ha segnato.

Gli utenti possono consultare esclusivamente i propri rimborsi e il totale
ancora dovuto. Gli admin possono consultare tutti i rimborsi, filtrarli per
persona e stato, segnarli come rimborsati o annullare la segnatura.

### Data registrazione

Generata automaticamente.

### Data operazione

Data reale della transazione.

### Fornitore

Esempi:

* Esselunga
* Macelleria Rossi
* Panetteria

### Unità

Valori:

* L/C
* E/G
* R/S
* CoCa
* Gruppo

Il valore viene preselezionato dalla branca associata al profilo. Per gli
utenti con ruolo `user` non è modificabile; gli admin possono selezionare una
branca diversa. Il backend forza sempre la branca del profilo per gli utenti
non admin.

### Importo

Valore monetario.

### Note

Campo obbligatorio. Deve descrivere brevemente il motivo del movimento.

Testo libero.

---

# API

## Health Check

GET /health

Risposta:

```json
{
  "status": "ok"
}
```

Utilizzato per rilevare il cold start di Render.

---

## Dashboard

GET /dashboard

---

## Movimenti

GET /movements

GET /movements/{id}

POST /movements

PUT /movements/{id}

DELETE /movements/{id}

---

## Settings

GET /settings

PUT /settings

---

## Export

GET /exports/excel

Genera e restituisce il file Excel.

---

## Utenti

Endpoint riservati agli admin:

GET /users

POST /users

PUT /users/{id}

La password è obbligatoria durante la registrazione e facoltativa durante la
modifica. Se omessa durante la modifica, quella esistente viene mantenuta.

---

## Rimborsi

GET /reimbursements

Restituisce riepilogo e movimenti da rimborsare. Per gli utenti normali include
esclusivamente i propri movimenti; per gli admin include tutti i movimenti.

PUT /reimbursements/{movement_id}

Endpoint riservato agli admin per segnare un rimborso come completato oppure
riportarlo allo stato da rimborsare.

---

# Gestione Cold Start

Render Free può mettere in pausa il backend.

Strategia:

1. Il frontend chiama `/health`
2. Timeout dopo 3 secondi
3. Mostra messaggio:

```text
Server in avvio...

Il server gratuito è stato sospeso per inattività.
Attendere qualche secondo.
```

4. Retry automatico ogni 3 secondi
5. Quando il backend risponde:

   * rimuove il banner
   * esegue l'operazione richiesta

---

# Database

## users

```sql
id uuid primary key

email text unique

password_hash text

name text

role text

branch text not null

created_at timestamptz
```

---

## camp_settings

```sql
id uuid primary key

camp_year integer

camp_name text

participants integer

quota_per_person numeric

max_budget numeric

cash_initial numeric

bank_initial numeric

created_at timestamptz
```

---

## movements

```sql
id uuid primary key

created_at timestamptz

operation_date date

type text

payment_method text

supplier text

unit text

amount numeric(10,2)

notes text

created_by uuid references users(id)
```

---

## movement_reimbursements

Contiene i collegamenti alle spese che necessitano di rimborso.

```sql
id uuid primary key

movement_id uuid unique not null references movements(id) on delete cascade

created_at timestamptz

reimbursed_at timestamptz nullable

reimbursed_by uuid nullable references users(id)
```

Il vincolo `unique` su `movement_id` garantisce che ogni movimento possa avere
al massimo una richiesta di rimborso.

Il backend permette di creare un collegamento esclusivamente per movimenti di
tipo `Uscita` con metodo di pagamento `Contanti`.

---

# Calcoli

## Spesa Eseguita

```text
SUM(uscite)
```

Le uscite con rimborso necessario sono incluse nella spesa eseguita.

---

## Budget Residuo

```text
spesa_massima - spesa_eseguita
```

---

## Saldo Contanti

```text
contanti_iniziali
+ entrate_contanti
- uscite_contanti
```

---

## Saldo Banca

```text
banca_iniziale
+ entrate_carta
- uscite_carta
```

---

# Excel

## Foglio Movimenti

Colonne:

* Data registrazione
* Data operazione
* Fornitore
* Unità
* Metodo
* Tipo
* Rimborso necessario
* Note
* Importo

---

## Foglio Riepilogo

Campi:

* Numero partecipanti
* Quota per partecipante
* Budget massimo
* Spesa eseguita
* Budget residuo
* Saldo contanti
* Saldo banca

---

# Roadmap V1

## Backend

* [ ] Setup FastAPI
* [ ] Setup SQLAlchemy
* [ ] Setup Alembic
* [ ] Setup JWT Auth
* [ ] CRUD Movimenti
* [ ] Dashboard
* [ ] Export Excel
* [ ] Health Check

## Frontend

* [ ] Setup Vue 3
* [ ] Setup Tailwind
* [ ] Login
* [ ] Dashboard
* [ ] Inserimento movimento
* [ ] Lista movimenti
* [ ] Modifica movimento
* [ ] Gestione cold start
* [ ] Installazione PWA

## Deploy

* [ ] Supabase PostgreSQL
* [ ] Render Backend
* [ ] Render Frontend
* [ ] Dominio personalizzato
