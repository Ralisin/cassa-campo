import asyncio
import uuid
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.models import Cassa, Movement, MovementType, PaymentMethod, User, UserRole
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


class FakeResponse:
    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return b"{}"


def make_movement(cassa: Cassa, user: User) -> Movement:
    return Movement(
        id=uuid.uuid4(),
        cassa_id=cassa.id,
        operation_date=date.today(),
        created_at=datetime.now(),
        type=MovementType.EXPENSE,
        payment_method=PaymentMethod.CASH,
        supplier="Supermercato",
        unit=cassa.unit,
        category="vitto",
        amount=Decimal("10.00"),
        notes="Spesa campo",
        created_by=user.id,
    )


def test_user_can_upload_download_and_delete_own_receipt(
    db, make_group, make_cassa, make_user, membership_of
) -> None:
    group = make_group()
    cassa = make_cassa(group, "E/G")
    alice = make_user(group, "alice@roma108.it", memberships=[(cassa, UserRole.USER)])
    movement = make_movement(cassa, alice)
    storage = FakeStorage()
    db.add(movement)
    db.flush()
    membership = membership_of(alice, cassa)

    receipt = asyncio.run(
        upload_receipt(
            movement.id, db, membership, storage, FakeUploadFile(b"receipt-content", "Scontrino spesa.pdf")
        )
    )
    download = download_receipt(movement.id, receipt.id, db, cassa, storage)
    delete_receipt(movement.id, receipt.id, db, membership, storage)

    assert receipt.filename == "Scontrino-spesa.pdf"
    assert receipt.size_bytes == len(b"receipt-content")
    assert storage.uploads[0][0].startswith(f"movements/{movement.id}/{receipt.id}-")
    assert download["url"].startswith("https://storage.example/")
    assert storage.deleted == [storage.uploads[0][0]]


def test_user_cannot_upload_receipt_to_another_users_movement(
    db, make_group, make_cassa, make_user, membership_of
) -> None:
    group = make_group()
    cassa = make_cassa(group, "E/G")
    owner = make_user(group, "alice@roma108.it", memberships=[(cassa, UserRole.USER)])
    other = make_user(group, "bob@roma108.it", memberships=[(cassa, UserRole.USER)])
    movement = make_movement(cassa, owner)
    storage = FakeStorage()
    db.add(movement)
    db.flush()

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            upload_receipt(
                movement.id, db, membership_of(other, cassa), storage, FakeUploadFile(b"receipt-content")
            )
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
