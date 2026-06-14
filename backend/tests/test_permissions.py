import uuid

import pytest
from fastapi import HTTPException

from app.dependencies import can_edit_movement, require_admin, require_operator
from app.models import User, UserRole


def make_user(role: UserRole) -> User:
    return User(
        id=uuid.uuid4(),
        email=f"{uuid.uuid4()}@example.it",
        name=role.value,
        password_hash="unused",
        role=role,
        branch="E/G",
    )


def test_user_can_edit_only_own_movements() -> None:
    user = make_user(UserRole.USER)

    assert can_edit_movement(user, user.id)
    assert not can_edit_movement(user, uuid.uuid4())


def test_admin_can_edit_other_users_movements() -> None:
    admin = make_user(UserRole.ADMIN)

    assert can_edit_movement(admin, uuid.uuid4())


def test_cashier_can_edit_other_users_movements() -> None:
    cashier = make_user(UserRole.CASHIER)

    assert can_edit_movement(cashier, uuid.uuid4())


def test_require_admin_accepts_admin() -> None:
    admin = make_user(UserRole.ADMIN)

    assert require_admin(admin) is admin


def test_require_admin_rejects_user() -> None:
    with pytest.raises(HTTPException) as exc_info:
        require_admin(make_user(UserRole.USER))

    assert exc_info.value.status_code == 403


def test_require_admin_rejects_cashier() -> None:
    with pytest.raises(HTTPException) as exc_info:
        require_admin(make_user(UserRole.CASHIER))

    assert exc_info.value.status_code == 403


def test_require_operator_accepts_admin_and_cashier() -> None:
    admin = make_user(UserRole.ADMIN)
    cashier = make_user(UserRole.CASHIER)

    assert require_operator(admin) is admin
    assert require_operator(cashier) is cashier


def test_require_operator_rejects_user() -> None:
    with pytest.raises(HTTPException) as exc_info:
        require_operator(make_user(UserRole.USER))

    assert exc_info.value.status_code == 403
