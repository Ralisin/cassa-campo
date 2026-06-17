import uuid
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import Branch, Movement, MovementType, PaymentMethod, User, UserRole
from app.receipt_storage import ReceiptStorage
from app.routers.receipts import delete_receipt, download_receipt, upload_receipt


class FakeUploadFile:
    def __init__(self, content: bytes, filename: str = "scontrino.pdf") -> None:
        self.content = content
        self.filename = filename
        self.content_type = "application/pdf"

    async def read(self) -> bytes:
        return self.content


class FakeStorage:
    def __init__(self) -> None:
        self.uploads: list[tuple[str, bytes, str]] = []
        self.deleted: list[str] = []

    def upload(self, storage_key: str, content: bytes, content_type: str) -> None:
        self.uploads.append((storage_key, content, content_type))

    def signed_url(self, storage_key: str, expires_in: int = 300) -> str:
        return f"https://storage.example/{storage_key}?expires={expires_in}"

    def delete(self, storage_key: str) -> None:
        self.deleted.append(storage_key)


@pytest.fixture
def db() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def make_user(name: str, role: UserRole = UserRole.USER) -> User:
    return User(
        id=uuid.uuid4(),
        email=f"{name.lower()}@example.it",
        name=name,
        password_hash="unused",
        role=role,
        branch=Branch.ESPLORATORI_GUIDE.value,
    )


def make_movement(user: User) -> Movement:
    return Movement(
        id=uuid.uuid4(),
        operation_date=date.today(),
        created_at=datetime.now(),
        type=MovementType.EXPENSE,
        payment_method=PaymentMethod.CASH,
        supplier="Supermercato",
        unit=Branch.ESPLORATORI_GUIDE.value,
        amount=Decimal("10.00"),
        notes="Spesa campo",
        created_by=user.id,
    )


class FakeResponse:
    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return b"{}"


@pytest.mark.anyio
async def test_user_can_upload_download_and_delete_own_receipt(db: Session) -> None:
    user = make_user("Alice")
    movement = make_movement(user)
    storage = FakeStorage()
    db.add_all([user, movement])
    db.commit()

    receipt = await upload_receipt(
        movement.id,
        db,
        user,
        storage,
        FakeUploadFile(b"receipt-content", "Scontrino spesa.pdf"),
    )
    download = download_receipt(movement.id, receipt.id, db, user, storage)
    delete_receipt(movement.id, receipt.id, db, user, storage)

    assert receipt.filename == "Scontrino-spesa.pdf"
    assert receipt.size_bytes == len(b"receipt-content")
    assert storage.uploads[0][0].startswith(f"movements/{movement.id}/{receipt.id}-")
    assert download["url"].startswith("https://storage.example/")
    assert storage.deleted == [storage.uploads[0][0]]


@pytest.mark.anyio
async def test_user_cannot_upload_receipt_to_another_users_movement(db: Session) -> None:
    owner = make_user("Alice")
    other_user = make_user("Bob")
    movement = make_movement(owner)
    storage = FakeStorage()
    db.add_all([owner, other_user, movement])
    db.commit()

    with pytest.raises(HTTPException) as error:
        await upload_receipt(
            movement.id,
            db,
            other_user,
            storage,
            FakeUploadFile(b"receipt-content"),
        )

    assert error.value.status_code == 403
    assert storage.uploads == []


def test_receipt_storage_deletes_single_object_with_delete_method() -> None:
    storage = ReceiptStorage(
        base_url="https://example.supabase.co",
        service_role_key="secret",
        bucket="receipts",
    )
    with patch("app.receipt_storage.urlopen", return_value=FakeResponse()) as urlopen_mock:
        storage.delete("movements/movement-id/receipt.pdf")

    request = urlopen_mock.call_args.args[0]
    assert request.get_method() == "DELETE"
    assert request.full_url.endswith("/storage/v1/object/receipts/movements/movement-id/receipt.pdf")
