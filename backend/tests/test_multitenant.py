"""Integration tests for the multi-tenant (group + cassa) behaviour.

Run against the Docker Postgres via the shared fixtures in conftest.py.
"""

from decimal import Decimal

import pytest

from app.models import CassaStatus, Membership, UserRole


def expense(**override) -> dict:
    payload = {
        "operation_date": "2026-06-20",
        "type": "uscita",
        "payment_method": "contanti",
        "supplier": "Esselunga",
        "category": "vitto",
        "amount": "25.00",
        "notes": "spesa",
    }
    payload.update(override)
    return payload


@pytest.fixture
def scenario(make_group, make_cassa, make_user):
    """A standard two-group scenario."""
    roma = make_group("roma108")
    milano = make_group("milano1")
    eg = make_cassa(roma, "E/G")
    lc = make_cassa(roma, "L/C")
    milano_eg = make_cassa(milano, "E/G")

    massimo = make_user(roma, "massimo@roma108.it", memberships=[(eg, UserRole.ADMIN)])
    luca = make_user(roma, "luca@roma108.it", memberships=[(eg, UserRole.CASHIER)])
    carlo = make_user(roma, "carlo@roma108.it", memberships=[(eg, UserRole.USER)])
    akela = make_user(roma, "akela@roma108.it", memberships=[(lc, UserRole.ADMIN)])
    capo = make_user(milano, "capo@milano1.it", memberships=[(milano_eg, UserRole.ADMIN)])

    return locals()


# --- Authentication & cassa context ---------------------------------------

def test_me_returns_memberships(client, scenario, auth):
    me = client.get("/auth/me", headers=auth("massimo@roma108.it")).json()
    assert me["email"] == "massimo@roma108.it"
    assert [(m["unit"], m["role"]) for m in me["memberships"]] == [("E/G", "admin")]


def test_missing_cassa_header_is_rejected(client, scenario, auth):
    res = client.get("/movements", headers=auth("massimo@roma108.it"))
    assert res.status_code == 400


def test_cassa_without_membership_is_forbidden(client, scenario, auth):
    # massimo has no membership in milano's cassa
    res = client.get("/movements", headers=auth("massimo@roma108.it", scenario["milano_eg"]))
    assert res.status_code == 403


# --- Movement scoping ------------------------------------------------------

def test_movement_unit_forced_to_cassa(client, scenario, auth):
    headers = auth("massimo@roma108.it", scenario["eg"])
    # client tries to sneak a different unit; server must force E/G
    res = client.post("/movements", json=expense(unit="R/S"), headers=headers)
    assert res.status_code == 201
    assert res.json()["unit"] == "E/G"


def test_movements_isolated_across_casse_and_groups(client, scenario, auth):
    roma_eg = auth("massimo@roma108.it", scenario["eg"])
    roma_lc = auth("akela@roma108.it", scenario["lc"])
    milano = auth("capo@milano1.it", scenario["milano_eg"])

    client.post("/movements", json=expense(supplier="Roma EG"), headers=roma_eg)
    client.post("/movements", json=expense(supplier="Roma LC"), headers=roma_lc)
    client.post("/movements", json=expense(supplier="Milano"), headers=milano)

    assert client.get("/movements", headers=roma_eg).json()["total"] == 1
    assert client.get("/movements", headers=roma_lc).json()["total"] == 1
    assert client.get("/movements", headers=milano).json()["total"] == 1
    suppliers = [m["supplier"] for m in client.get("/movements", headers=roma_eg).json()["items"]]
    assert suppliers == ["Roma EG"]


def test_cannot_read_movement_from_another_cassa(client, scenario, auth):
    roma_eg = auth("massimo@roma108.it", scenario["eg"])
    roma_lc = auth("akela@roma108.it", scenario["lc"])
    movement_id = client.post("/movements", json=expense(), headers=roma_eg).json()["id"]
    assert client.get(f"/movements/{movement_id}", headers=roma_eg).status_code == 200
    assert client.get(f"/movements/{movement_id}", headers=roma_lc).status_code == 404


def test_user_can_edit_only_own_movement(client, scenario, auth):
    carlo = auth("carlo@roma108.it", scenario["eg"])
    massimo = auth("massimo@roma108.it", scenario["eg"])
    carlo_mv = client.post("/movements", json=expense(supplier="Carlo"), headers=carlo).json()["id"]
    massimo_mv = client.post("/movements", json=expense(supplier="Massimo"), headers=massimo).json()["id"]

    # carlo (user) cannot edit massimo's movement
    assert client.put(f"/movements/{massimo_mv}", json=expense(notes="x"), headers=carlo).status_code == 403
    # carlo can edit his own
    assert client.put(f"/movements/{carlo_mv}", json=expense(notes="ok"), headers=carlo).status_code == 200
    # admin can edit anyone's
    assert client.put(f"/movements/{carlo_mv}", json=expense(notes="byadmin"), headers=massimo).status_code == 200


# --- Dashboard / settings / export ----------------------------------------

def test_dashboard_is_scoped(client, scenario, auth):
    roma_eg = auth("massimo@roma108.it", scenario["eg"])
    milano = auth("capo@milano1.it", scenario["milano_eg"])
    client.post("/movements", json=expense(amount="25.00"), headers=roma_eg)
    assert Decimal(client.get("/dashboard", headers=roma_eg).json()["spent"]) == Decimal("25.00")
    assert Decimal(client.get("/dashboard", headers=milano).json()["spent"]) == Decimal("0")


def test_settings_are_per_cassa(client, scenario, auth):
    roma_eg = auth("massimo@roma108.it", scenario["eg"])
    roma_lc = auth("akela@roma108.it", scenario["lc"])
    body = {
        "camp_year": 2026,
        "camp_name": "Campo EG",
        "participants": 10,
        "quota_per_person": "50",
        "cash_initial": "100",
        "category_budgets": {},
    }
    assert client.put("/settings", json=body, headers=roma_eg).status_code == 200
    assert client.get("/settings", headers=roma_eg).json()["camp_name"] == "Campo EG"
    # the L/C cassa has no settings yet
    assert client.get("/settings", headers=roma_lc).status_code == 404


def test_export_requires_operator_and_is_scoped(client, scenario, auth):
    assert client.get("/exports/excel", headers=auth("carlo@roma108.it", scenario["eg"])).status_code == 403
    assert client.get("/exports/excel", headers=auth("massimo@roma108.it", scenario["eg"])).status_code == 200


# --- Reimbursements --------------------------------------------------------

def test_reimbursements_scoped_and_role_filtered(client, scenario, auth):
    carlo = auth("carlo@roma108.it", scenario["eg"])
    massimo = auth("massimo@roma108.it", scenario["eg"])
    client.post("/movements", json=expense(needs_reimbursement=True, supplier="Carlo"), headers=carlo)
    client.post("/movements", json=expense(needs_reimbursement=True, supplier="Massimo"), headers=massimo)

    # admin sees both, plain user only their own
    assert client.get("/reimbursements", headers=massimo).json()["pending_count"] == 2
    assert client.get("/reimbursements", headers=carlo).json()["pending_count"] == 1


# --- Transfers -------------------------------------------------------------

def test_transfer_requires_operator(client, scenario, auth):
    carlo = auth("carlo@roma108.it", scenario["eg"])
    payload = {"operation_date": "2026-06-20", "type": "prelievo", "amount": "10.00", "notes": "giro"}
    assert client.post("/transfers", json=payload, headers=carlo).status_code == 403


# --- Notifications ---------------------------------------------------------

def test_notifications_target_cassa_admins(client, scenario, auth):
    carlo = auth("carlo@roma108.it", scenario["eg"])
    client.post("/movements", json=expense(), headers=carlo)
    # the E/G admin (massimo) receives the notification
    massimo_notifs = client.get("/notifications", headers=auth("massimo@roma108.it", scenario["eg"])).json()
    assert massimo_notifs["unread_count"] == 1
    # the L/C admin (akela) does not
    akela_notifs = client.get("/notifications", headers=auth("akela@roma108.it", scenario["lc"])).json()
    assert akela_notifs["unread_count"] == 0


# --- User & cassa management ----------------------------------------------

def test_admin_creates_user_with_multi_cassa_memberships(client, scenario, auth):
    headers = auth("massimo@roma108.it", scenario["eg"])
    res = client.post(
        "/users",
        json={
            "email": "nuovo@roma108.it",
            "name": "Nuovo",
            "password": "password123",
            "memberships": [
                {"unit": "E/G", "role": "user"},
                {"unit": "L/C", "role": "admin"},
            ],
        },
        headers=headers,
    )
    assert res.status_code == 201
    units = {(m["unit"], m["role"]) for m in res.json()["memberships"]}
    assert units == {("E/G", "user"), ("L/C", "admin")}


def test_user_email_must_match_group_domain(client, scenario, auth):
    headers = auth("massimo@roma108.it", scenario["eg"])
    res = client.post(
        "/users",
        json={
            "email": "x@altrodominio.it",
            "name": "X",
            "password": "password123",
            "memberships": [{"unit": "E/G", "role": "user"}],
        },
        headers=headers,
    )
    assert res.status_code == 400


def test_user_listing_isolated_per_group(client, scenario, auth):
    roma = client.get("/users", headers=auth("massimo@roma108.it", scenario["eg"])).json()
    milano = client.get("/users", headers=auth("capo@milano1.it", scenario["milano_eg"])).json()
    assert {u["email"] for u in roma} == {
        "massimo@roma108.it",
        "luca@roma108.it",
        "carlo@roma108.it",
        "akela@roma108.it",
    }
    assert {u["email"] for u in milano} == {"capo@milano1.it"}


def test_non_admin_cannot_manage_users(client, scenario, auth):
    assert client.get("/users", headers=auth("carlo@roma108.it", scenario["eg"])).status_code == 403


def test_cannot_remove_last_admin_of_a_cassa(client, scenario, auth):
    headers = auth("massimo@roma108.it", scenario["eg"])
    massimo_id = client.get("/auth/me", headers=headers).json()["id"]
    # massimo is the only admin of E/G; demoting to user must fail
    res = client.put(
        f"/users/{massimo_id}",
        json={
            "email": "massimo@roma108.it",
            "name": "Massimo",
            "memberships": [{"unit": "E/G", "role": "user"}],
        },
        headers=headers,
    )
    assert res.status_code == 400


def test_casse_listing_and_creation(client, scenario, auth):
    headers = auth("massimo@roma108.it", scenario["eg"])
    casse = client.get("/casse", headers=headers).json()
    units = {c["unit"] for c in casse}
    assert units == {"E/G", "L/C"}
    assert {c["kind"] for c in casse} == {"campo"}
    assert {c["status"] for c in casse} == {"aperta"}
    rs_campo = client.post("/casse", json={"unit": "R/S", "kind": "campo", "year": 2026}, headers=headers)
    assert rs_campo.status_code == 201
    created = client.post("/casse", json={"unit": "R/S", "kind": "anno", "year": 2026}, headers=headers)
    assert created.status_code == 201
    assert created.json()["kind"] == "anno"
    assert client.post("/casse", json={"unit": "R/S", "kind": "anno", "year": 2027}, headers=headers).status_code == 409


def test_cashier_can_manage_casse(client, scenario, auth):
    headers = auth("luca@roma108.it", scenario["eg"])
    created = client.post("/casse", json={"unit": "E/G", "kind": "anno", "year": 2026}, headers=headers)
    assert created.status_code == 201
    assert created.json()["kind"] == "anno"
    assert client.put(f"/casse/{created.json()['id']}/close", headers=headers).status_code == 200


def test_operator_cannot_close_cassa_where_they_are_plain_user(client, scenario, auth, db):
    db.add(Membership(user_id=scenario["massimo"].id, cassa_id=scenario["lc"].id, role=UserRole.USER))
    db.flush()
    headers = auth("massimo@roma108.it", scenario["eg"])
    assert client.put(f"/casse/{scenario['lc'].id}/close", headers=headers).status_code == 403


def test_closed_cassa_is_read_only_and_next_year_can_be_opened(client, scenario, auth, db):
    headers = auth("massimo@roma108.it", scenario["eg"])
    client.post("/movements", json=expense(supplier="Storico"), headers=headers)

    assert client.put(f"/casse/{scenario['lc'].id}/close", headers=headers).status_code == 200
    close = client.put(f"/casse/{scenario['eg'].id}/close", headers=headers)
    assert close.status_code == 200
    assert close.json()["status"] == "chiusa"
    db.refresh(scenario["eg"])
    assert scenario["eg"].status == CassaStatus.CLOSED

    assert client.get("/movements", headers=headers).json()["total"] == 1
    assert client.post("/movements", json=expense(supplier="Bloccato"), headers=headers).status_code == 403
    assert client.put("/settings", json={
        "camp_year": 2027,
        "camp_name": "Campo chiuso",
        "participants": 1,
        "quota_per_person": "1.00",
        "cash_initial": "0.00",
        "category_budgets": {},
    }, headers=headers).status_code == 403

    new_cassa = client.post(
        "/casse",
        json={"unit": "E/G", "kind": "campo", "year": scenario["eg"].year + 1},
        headers=headers,
    )
    assert new_cassa.status_code == 201
    assert new_cassa.json()["status"] == "aperta"


# --- System administrator --------------------------------------------------

def test_system_admin_is_bootstrapped_and_hidden_from_group_admins(client, scenario, auth, db):
    system_headers = auth("massimo@admin.it", password="CassaCampo2026!")
    me = client.get("/auth/me", headers=system_headers).json()
    assert me["is_system_admin"] is True
    assert me["memberships"] == []

    scenario["massimo"].is_system_admin = True
    db.flush()
    users = client.get("/users", headers=auth("akela@roma108.it", scenario["lc"])).json()
    assert "massimo@roma108.it" not in {user["email"] for user in users}


def test_system_admin_can_open_any_cassa_without_membership(client, scenario, auth):
    headers = auth("massimo@admin.it", scenario["milano_eg"], password="CassaCampo2026!")
    res = client.get("/dashboard", headers=headers)
    assert res.status_code == 200


def test_system_admin_manages_users_for_selected_group(client, scenario, auth):
    headers = auth("massimo@admin.it", scenario["eg"], password="CassaCampo2026!")
    users = client.get("/users", headers=headers).json()
    assert {user["email"] for user in users} == {
        "massimo@roma108.it",
        "luca@roma108.it",
        "carlo@roma108.it",
        "akela@roma108.it",
    }

    res = client.post(
        "/users",
        json={
            "email": "sistema-crea@roma108.it",
            "name": "Creato da sistema",
            "password": "password123",
            "memberships": [{"unit": "E/G", "role": "cashier"}],
        },
        headers=headers,
    )
    assert res.status_code == 201
    assert res.json()["group_id"] == str(scenario["roma"].id)


def test_system_overview_and_group_delete(client, scenario, auth):
    headers = auth("massimo@admin.it", password="CassaCampo2026!")
    overview = client.get("/system/overview", headers=headers).json()
    assert {group["slug"] for group in overview["groups"]} == {"milano1", "roma108"}

    milano_id = next(group["id"] for group in overview["groups"] if group["slug"] == "milano1")
    assert client.delete(f"/system/groups/{milano_id}", headers=headers).status_code == 204
    overview = client.get("/system/overview", headers=headers).json()
    assert {group["slug"] for group in overview["groups"]} == {"roma108"}


def test_system_admin_can_delete_single_cassa(client, scenario, auth):
    system_headers = auth("massimo@admin.it", password="CassaCampo2026!")
    assert client.delete(f"/system/casse/{scenario['lc'].id}", headers=system_headers).status_code == 204

    overview = client.get("/system/overview", headers=system_headers).json()
    roma = next(group for group in overview["groups"] if group["slug"] == "roma108")
    assert {cassa["id"] for cassa in roma["casse"]} == {str(scenario["eg"].id)}


def test_non_system_admin_cannot_use_system_api(client, scenario, auth):
    res = client.get("/system/overview", headers=auth("massimo@roma108.it", scenario["eg"]))
    assert res.status_code == 403
    delete_res = client.delete(f"/system/casse/{scenario['lc'].id}", headers=auth("massimo@roma108.it", scenario["eg"]))
    assert delete_res.status_code == 403
