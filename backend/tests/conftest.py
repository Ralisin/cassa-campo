"""Shared test fixtures running against the local Docker Postgres.

A dedicated `cassa_campo_test` database is created (and migrated) once per
session, isolated from the dev database. Each test runs inside a transaction
that is rolled back at the end, so tests never see each other's data.
"""

import os

# Point the whole app at the test database *before* anything imports app config.
SERVER_URL = "postgresql+psycopg://cassa_campo:cassa_campo@localhost:5432/cassa_campo"
TEST_URL = "postgresql+psycopg://cassa_campo:cassa_campo@localhost:5432/cassa_campo_test"
os.environ["DATABASE_URL"] = TEST_URL

import pytest  # noqa: E402
from sqlalchemy import create_engine, select, text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.models import Cassa, Group, Membership, User, UserRole  # noqa: E402


@pytest.fixture(scope="session")
def engine():
    admin = create_engine(SERVER_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text("DROP DATABASE IF EXISTS cassa_campo_test WITH (FORCE)"))
        conn.execute(text("CREATE DATABASE cassa_campo_test"))
    admin.dispose()

    from alembic import command
    from alembic.config import Config

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", TEST_URL)
    command.upgrade(cfg, "head")

    eng = create_engine(TEST_URL)
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine):
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db):
    from fastapi.testclient import TestClient

    from app.core.database import get_db
    from app.main import app

    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# --- Factory helpers -------------------------------------------------------

@pytest.fixture
def make_group(db):
    def _make(slug: str = "roma108", domain: str | None = None) -> Group:
        group = Group(slug=slug, name=slug.capitalize(), email_domain=domain or f"{slug}.it")
        db.add(group)
        db.flush()
        return group

    return _make


@pytest.fixture
def make_cassa(db):
    def _make(group: Group, unit: str) -> Cassa:
        cassa = Cassa(group_id=group.id, unit=unit)
        db.add(cassa)
        db.flush()
        return cassa

    return _make


@pytest.fixture
def make_user(db):
    def _make(
        group: Group,
        email: str,
        *,
        password: str = "password123",
        memberships: list[tuple[Cassa, UserRole]] | None = None,
    ) -> User:
        user = User(
            email=email.lower(),
            name=email.split("@")[0].capitalize(),
            password_hash=hash_password(password),
            group_id=group.id,
        )
        db.add(user)
        db.flush()
        for cassa, role in memberships or []:
            db.add(Membership(user_id=user.id, cassa_id=cassa.id, role=role))
        db.flush()
        return user

    return _make


@pytest.fixture
def membership_of(db):
    def _get(user: User, cassa: Cassa) -> Membership:
        return db.scalar(
            select(Membership).where(
                Membership.user_id == user.id, Membership.cassa_id == cassa.id
            )
        )

    return _get


@pytest.fixture
def auth(client):
    """Return a helper producing auth headers (optionally with a cassa)."""

    def _auth(email: str, cassa: Cassa | None = None, password: str = "password123") -> dict:
        token = client.post(
            "/auth/login", json={"email": email, "password": password}
        ).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        if cassa is not None:
            headers["X-Cassa-Id"] = str(cassa.id)
        return headers

    return _auth
