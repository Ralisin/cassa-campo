import pytest
from fastapi import HTTPException

from app.core.security import verify_password
from app.models import User, UserRole
from app.routers.users import create_user, update_user
from app.schemas import MembershipInput, UserCreate, UserUpdate


@pytest.fixture
def setup(db, make_group, make_cassa, make_user, membership_of):
    group = make_group()
    cassa = make_cassa(group, "E/G")
    admin = make_user(group, "admin@roma108.it", memberships=[(cassa, UserRole.ADMIN)])
    return db, group, cassa, admin, membership_of(admin, cassa)


def test_admin_can_create_and_update_user(setup) -> None:
    db, group, cassa, admin, admin_membership = setup

    created = create_user(
        UserCreate(
            email="UTENTE@roma108.it",
            name="Utente",
            password="password",
            memberships=[MembershipInput(unit="R/S", role=UserRole.USER)],
        ),
        db,
        admin,
        admin_membership,
    )
    assert created.email == "utente@roma108.it"
    assert {(m.unit.value, m.role) for m in created.memberships} == {("R/S", UserRole.USER)}

    updated = update_user(
        created.id,
        UserUpdate(
            email="nuova@roma108.it",
            name="Nuovo Nome",
            password="nuova-password",
            memberships=[MembershipInput(unit="CoCa", role=UserRole.ADMIN)],
        ),
        db,
        admin,
        admin_membership,
    )

    assert updated.email == "nuova@roma108.it"
    assert updated.name == "Nuovo Nome"
    assert {(m.unit.value, m.role) for m in updated.memberships} == {("CoCa", UserRole.ADMIN)}

    stored = db.get(User, created.id)
    assert verify_password("nuova-password", stored.password_hash)


def test_user_email_must_match_group_domain(setup) -> None:
    db, group, cassa, admin, admin_membership = setup
    with pytest.raises(HTTPException) as exc_info:
        create_user(
            UserCreate(
                email="x@altrodominio.it",
                name="X",
                password="password",
                memberships=[MembershipInput(unit="E/G", role=UserRole.USER)],
            ),
            db,
            admin,
            admin_membership,
        )
    assert exc_info.value.status_code == 400


def test_last_admin_of_a_cassa_cannot_be_demoted(setup) -> None:
    db, group, cassa, admin, admin_membership = setup
    with pytest.raises(HTTPException) as exc_info:
        update_user(
            admin.id,
            UserUpdate(
                email="admin@roma108.it",
                name="Admin",
                memberships=[MembershipInput(unit="E/G", role=UserRole.USER)],
            ),
            db,
            admin,
            admin_membership,
        )
    assert exc_info.value.status_code == 400
