import pytest

from app.core.security import hash_password, verify_password


def test_hash_and_verify_password() -> None:
    password_hash = hash_password("password")

    assert password_hash != "password"
    assert verify_password("password", password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_password_longer_than_bcrypt_limit_is_rejected() -> None:
    with pytest.raises(ValueError, match="72"):
        hash_password("a" * 73)
