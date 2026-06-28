# Piano: Multi-tenant (Gruppo) + Casse per Unità

> Stato vivo del progetto di refactoring verso multi-tenancy.
> Aggiornare le checkbox man mano. Pensato per essere ripreso su più sessioni
> (limiti di utilizzo). Ogni fase è il più possibile autoconclusiva.

## Decisioni prese (confermate)

1. **Isolamento dati** → colonna `cassa_id` su ogni riga + filtro sempre attivo lato backend.
   Niente tabelle fisiche separate.
2. **Ruolo per cassa** → un utente può avere ruoli diversi su casse diverse
   (admin di E/G, user di L/C). Ruolo vive sulla *membership*, non sull'utente.
3. **Onboarding gestito da admin** → il gruppo è ricavato/creato dal dominio email
   (`massimo@roma108.it` → gruppo `roma108`, domain `roma108.it`). Primo admin di
   ogni gruppo via script di bootstrap. Nessuna registrazione aperta.

## Modello dati target

### Nuove tabelle
- **groups** (tenant): `id`, `slug` (es. `roma108`, unique), `name`,
  `email_domain` (es. `roma108.it`, unique), `created_at`.
- **casse**: `id`, `group_id`→groups, `unit` (enum Branch), `created_at`,
  `unique(group_id, unit)`. Una cassa = (gruppo, unità).
- **memberships**: `id`, `user_id`→users, `cassa_id`→casse,
  `role` (admin/cashier/user), `unique(user_id, cassa_id)`.

### Tabelle modificate
- **users**: aggiungere `group_id`→groups (NOT NULL). **Rimuovere** `branch` e
  `role` (migrano su memberships). Email resta unique globale.
- **camp_settings**: aggiungere `cassa_id`→casse. Una riga settings "corrente" per cassa.
- **movements**: aggiungere `cassa_id`→casse (NOT NULL). Il campo `unit` non è più
  scelto dall'utente: coincide con `cassa.unit` (mantenuto sincronizzato per export).
- **treasury_transfers**: aggiungere `cassa_id`→casse (NOT NULL).
- **movement_reimbursements / movement_receipts / notifications**: nessuna colonna
  nuova; lo scope arriva via `movement.cassa_id`. Le query si filtrano joinando il movement.
  Le notifiche vanno agli admin **della cassa** del movimento.

### Invariate
- **expense_categories**: restano globali/condivise tra tutti i gruppi.
- **camp_category_budgets**: invariata (legata a `settings_id`).

## Meccanica di scope (auth)

- `/auth/login` invariato (ritorna token con `user_id`).
- `/auth/me` ritorna user + **lista membership** `[{cassa_id, group, unit, role}]`.
- Frontend: 1 membership → selezione automatica; >1 → **portale di scelta cassa**.
  Cassa attiva salvata in `localStorage`.
- Ogni richiesta invia header `X-Cassa-Id`. Nuova dependency
  `get_current_membership(user, X-Cassa-Id)` valida l'appartenenza e restituisce
  `(user, cassa, role)`. `require_admin`/`require_operator` usano il ruolo **della
  membership**, non più un ruolo globale.
- (Alternativa scartata: re-mint del token con claim cassa. Header è più semplice e stateless.)

---

## FASI

### FASE 0 — Fondamenta dati (backend, sequenziale, BLOCCANTE) ✅ FATTA
Nessun worker parallelo: tutto il resto dipende da qui.
- [x] models.py: `Group`, `Cassa`, `Membership`; aggiornare `User`; aggiungere
      `cassa_id` a `Movement`, `TreasuryTransfer`, `CampSettings`.
- [x] Migrazione Alembic `0011_multitenant`:
  - crea `groups`, `casse`, `memberships`;
  - aggiunge le colonne `cassa_id` (+ `users.group_id`);
  - **data migration**: crea un gruppo per ogni dominio email; crea le casse per
    ogni `unit` di users/movements; mappa movements/transfers alla cassa; assegna
    `camp_settings` alla cassa del primo admin; crea memberships da `(branch, role)`;
  - infine rende `cassa_id`/`group_id` NOT NULL e droppa `users.branch`/`users.role`.
  - downgrade reversibile (ripristina role/branch da una membership).
- [x] `create_admin.py`: crea gruppo + cassa + membership admin (bootstrap).
- [x] Test migrazione su Postgres locale (Docker): upgrade+backfill, downgrade,
      re-upgrade, ORM mappers, create_admin — tutto verde.

**Deliverable:** schema migrato, DB esistente convertito senza perdita dati. ✅

> ⚠️ **NON ancora applicata alla produzione.** Applicare `alembic upgrade head` su
> Supabase SOLO insieme al deploy di FASE 1+2: il codice attuale dei router/services
> usa ancora `user.role`/`user.branch` e si romperebbe contro lo schema migrato.

### FASE 1 — Scope & dependencies (backend, sequenziale) ✅ FATTA
- [x] dependencies.py: `get_current_membership` (valida header `X-Cassa-Id`),
      `CurrentMembership`, `CurrentCassa`, `require_admin`/`require_operator` sul
      ruolo della membership; `can_edit_movement(membership, created_by)`.
- [x] schemas.py: `GroupRead`, `CassaRead`, `MembershipRead`, `MembershipInput`;
      `UserRead` con memberships; `UserCreate`/`UserUpdate` con lista membership;
      `MovementInput.unit` opzionale (forzato = cassa.unit).
- [x] auth.py: `/auth/me` ritorna user + memberships (via `services.user_to_read`).
**Deliverable:** infrastruttura di scope pronta. ✅

### FASE 2 — Applicare lo scope a tutte le query (backend) ✅ FATTA
- [x] movements.py: filtro `cassa_id` su list/get/create/update/delete; create/update
      settano `cassa_id` e forzano `unit = cassa.unit`; creators scoped.
- [x] services.py (dashboard): tutte le SUM/saldi/settings/categorie filtrate per
      `cassa_id` (riscritta la query categorie per evitare ambiguità di join).
- [x] settings.py: settings per cassa (`latest_settings(db, cassa_id)`).
- [x] transfers.py: filtro + set `cassa_id`; `validate_available_balance` per cassa.
- [x] reimbursements.py: filtro via `Movement.cassa_id` + ruolo membership.
- [x] exports.py: export della cassa attiva (movimenti/transfer/settings scoped).
- [x] notifications.py + notification_service.py: notifiche agli admin/cashier della
      cassa (via memberships); liste notifiche scoped alla cassa attiva.
- [x] receipts.py: il movement deve appartenere alla cassa attiva.
- [x] **Test end-to-end su Postgres locale**: scope, isolamento cross-cassa e
      cross-gruppo, header mancante→400, cassa non autorizzata→403, dashboard/settings/
      export/users scoped. Tutto verde.
**Deliverable:** backend completamente isolato per cassa. ✅

> ✅ **Test di integrazione aggiunti:** `tests/conftest.py` (Postgres docker, DB di
> test dedicato, sessione transazionale, TestClient, factory) + `tests/test_multitenant.py`
> (19 test HTTP su scope/isolamento/ruoli/gestione). `pytest` → 22 passed.
>
> 🔧 **Sotto-task residuo (FASE 2b):** i 13 file di test legacy pre-multitenant sono
> esclusi dalla collection (`collect_ignore` in conftest) perche' costruiscono
> `User(role=, branch=)` e chiamano le vecchie firme dei router. Vanno portati o
> rimpiazzati riusando le fixture di conftest.

### FASE 3 — Gestione gruppo/utenti/casse (backend) ✅ FATTA
- [x] users.py: scope al gruppo dell'admin; CRUD utenti + sync memberships
      (assegna/rimuovi cassa+ruolo, cassa creata on-demand); dominio email validato;
      vincolo "ultimo admin" per-cassa.
- [x] casse.py: `GET /casse` (casse del gruppo) e `POST /casse` (crea cassa per
      un'unità), admin-only, registrato in main.py.
**Deliverable:** un admin gestisce utenti e casse del proprio gruppo via API. ✅

### FASE 4 — Frontend: sessione, portale, header (frontend)
- [ ] session.js: `memberships`, `activeCassa`, `setCassa`, ruolo derivato dalla cassa attiva.
- [ ] api.js: iniettare header `X-Cassa-Id` dalla cassa attiva.
- [ ] router.js: guard che redirige al portale se nessuna cassa selezionata;
      route `/seleziona-cassa`.
- [ ] Nuova view `CassaSelectView`: lista casse dell'utente (gruppo+unità+ruolo).
- [ ] App.vue: header mostra gruppo/unità attiva + switch cassa.
**Deliverable:** login → (auto o scelta) cassa → app opera sulla cassa scelta.

### FASE 5 — Frontend: viste e gestione (frontend)
> Parallelizzabile: Worker A viste dati, Worker B gestione utenti/casse.
- [ ] MovementFormView: unità fissata dalla cassa (non selezionabile).
- [ ] Dashboard/Movements/Summary/Reimbursements: nessuna logica branch globale residua.
- [ ] UsersView: gestione utenti del gruppo + assegnazione casse/ruoli.
- [ ] Nuova UI gestione casse (crea unità mancante).
**Deliverable:** UI completa multi-cassa.

### FASE 6 — Rifinitura
- [ ] Aggiornare `cassa-campo.md` (architettura) e README.
- [ ] Test end-to-end manuali con 2 gruppi e utente multi-cassa.
- [ ] Verifica PWA/offlineQueue rispetti la cassa attiva.

---

## Note di rischio
- La data-migration è il punto critico: testare su copia prima di toccare il DB reale.
- `offlineQueue.js` accoda richieste: deve salvare anche la cassa attiva al momento dell'accodamento.
- Export Excel e notifiche: ricontrollare che non leakino dati tra casse.

## Suggerimento sequencing rispetto ai limiti
- Sessione 1: FASE 0 (+1 se avanza budget).
- Sessione 2: FASE 1 + FASE 2 (con worker paralleli).
- Sessione 3: FASE 3 + FASE 4.
- Sessione 4: FASE 5 + FASE 6.
