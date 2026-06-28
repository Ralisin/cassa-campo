import uuid

import pytest
from fastapi import HTTPException

from app.dependencies import can_edit_movement, require_admin, require_operator
from app.models import Membership, UserRole


def membership(role: UserRole) -> Membership:
    return Membership(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        cassa_id=uuid.uuid4(),
        role=role,
    )


def test_user_can_edit_only_own_movements() -> None:
    member = membership(UserRole.USER)
    assert can_edit_movement(member, member.user_id)
    assert not can_edit_movement(member, uuid.uuid4())


def test_admin_can_edit_other_users_movements() -> None:
    assert can_edit_movement(membership(UserRole.ADMIN), uuid.uuid4())


def test_cashier_can_edit_other_users_movements() -> None:
    assert can_edit_movement(membership(UserRole.CASHIER), uuid.uuid4())


def test_require_admin_accepts_admin() -> None:
    member = membership(UserRole.ADMIN)
    assert require_admin(member) is member


def test_require_admin_rejects_user() -> None:
    with pytest.raises(HTTPException) as exc_info:
        require_admin(membership(UserRole.USER))
    assert exc_info.value.status_code == 403


def test_require_admin_rejects_cashier() -> None:
    with pytest.raises(HTTPException) as exc_info:
        require_admin(membership(UserRole.CASHIER))
    assert exc_info.value.status_code == 403


def test_require_operator_accepts_admin_and_cashier() -> None:
    admin = membership(UserRole.ADMIN)
    cashier = membership(UserRole.CASHIER)
    assert require_operator(admin) is admin
    assert require_operator(cashier) is cashier


def test_require_operator_rejects_user() -> None:
    with pytest.raises(HTTPException) as exc_info:
        require_operator(membership(UserRole.USER))
    assert exc_info.value.status_code == 403
