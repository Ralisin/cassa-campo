"""Integration tests for the multi-tenant (group + cassa) behaviour.

Run against the Docker Postgres via the shared fixtures in conftest.py.
"""

from decimal import Decimal

import pytest

from app.models import UserRole


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
    units = {c["unit"] for c in client.get("/casse", headers=headers).json()}
    assert units == {"E/G", "L/C"}
    assert client.post("/casse", json={"unit": "R/S"}, headers=headers).status_code == 201
    assert client.post("/casse", json={"unit": "E/G"}, headers=headers).status_code == 409
