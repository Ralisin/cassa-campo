import re
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from app.audit_service import write_audit
from app.core.config import settings
from app.dependencies import CurrentCassa, CurrentMembership, DbSession, WritableMembership, can_edit_movement
from app.models import Membership, Movement, MovementReceipt, MovementReimbursement
from app.receipt_storage import ReceiptStorage, get_receipt_storage
from app.schemas import MovementReceiptRead

router = APIRouter(prefix="/movements/{movement_id}/receipts", tags=["receipts"])

ALLOWED_RECEIPT_TYPES = {"image/jpeg", "image/png", "application/pdf"}


def get_movement_or_404(db: DbSession, movement_id: uuid.UUID, cassa_id: uuid.UUID) -> Movement:
    movement = db.scalar(
        select(Movement)
        .options(
            joinedload(Movement.reimbursement).joinedload(MovementReimbursement.reimbursed_by_user),
            joinedload(Movement.creator),
            selectinload(Movement.receipts),
        )
        .where(
            Movement.id == movement_id,
            Movement.cassa_id == cassa_id,
            Movement.deleted_at.is_(None),
        )
    )
    if not movement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movement not found")
    return movement


def get_receipt_or_404(
    db: DbSession,
    movement_id: uuid.UUID,
    receipt_id: uuid.UUID,
) -> MovementReceipt:
    receipt = db.scalar(
        select(MovementReceipt).where(
            MovementReceipt.id == receipt_id,
            MovementReceipt.movement_id == movement_id,
        )
    )
    if not receipt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")
    return receipt


def safe_filename(filename: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9._-]+", "-", filename.strip()).strip(".-")
    return clean[:120] or "receipt"


def ensure_can_edit_receipts(membership: Membership, movement: Movement) -> None:
    if not can_edit_movement(membership, movement.created_by):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")


@router.get("", response_model=list[MovementReceiptRead])
def list_receipts(
    movement_id: uuid.UUID,
    db: DbSession,
    cassa: CurrentCassa,
) -> list[MovementReceiptRead]:
    movement = get_movement_or_404(db, movement_id, cassa.id)
    return [MovementReceiptRead.model_validate(receipt) for receipt in movement.receipts]


@router.post("", response_model=MovementReceiptRead, status_code=status.HTTP_201_CREATED)
async def upload_receipt(
    movement_id: uuid.UUID,
    db: DbSession,
    membership: WritableMembership,
    storage: Annotated[ReceiptStorage, Depends(get_receipt_storage)],
    file: UploadFile = File(...),
) -> MovementReceiptRead:
    movement = get_movement_or_404(db, movement_id, membership.cassa_id)
    ensure_can_edit_receipts(membership, movement)
    if file.content_type not in ALLOWED_RECEIPT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Sono ammessi solo PDF, PNG e JPEG",
        )
    content = await file.read()
    max_size = settings.max_receipt_size_mb * 1024 * 1024
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File vuoto")
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Lo scontrino supera il limite di {settings.max_receipt_size_mb} MB",
        )
    receipt_id = uuid.uuid4()
    filename = safe_filename(file.filename or "receipt")
    storage_key = f"movements/{movement_id}/{receipt_id}-{filename}"
    storage.upload(storage_key, content, file.content_type)
    receipt = MovementReceipt(
        id=receipt_id,
        movement_id=movement_id,
        uploaded_by=membership.user_id,
        filename=filename,
        content_type=file.content_type,
        size_bytes=len(content),
        storage_key=storage_key,
    )
    db.add(receipt)
    write_audit(
        db,
        action="receipt_uploaded",
        entity_type="receipt",
        entity_id=receipt.id,
        cassa_id=membership.cassa_id,
        user_id=membership.user_id,
        summary=f"Caricato scontrino {receipt.filename}",
        details={"movement_id": str(movement_id), "size_bytes": receipt.size_bytes},
    )
    db.commit()
    db.refresh(receipt)
    return MovementReceiptRead.model_validate(receipt)


@router.get("/{receipt_id}")
def download_receipt(
    movement_id: uuid.UUID,
    receipt_id: uuid.UUID,
    db: DbSession,
    cassa: CurrentCassa,
    storage: Annotated[ReceiptStorage, Depends(get_receipt_storage)],
) -> dict[str, str]:
    get_movement_or_404(db, movement_id, cassa.id)
    receipt = get_receipt_or_404(db, movement_id, receipt_id)
    return {"url": storage.signed_url(receipt.storage_key)}


@router.delete("/{receipt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_receipt(
    movement_id: uuid.UUID,
    receipt_id: uuid.UUID,
    db: DbSession,
    membership: WritableMembership,
    storage: Annotated[ReceiptStorage, Depends(get_receipt_storage)],
) -> None:
    movement = get_movement_or_404(db, movement_id, membership.cassa_id)
    ensure_can_edit_receipts(membership, movement)
    receipt = get_receipt_or_404(db, movement_id, receipt_id)
    storage.delete(receipt.storage_key)
    write_audit(
        db,
        action="receipt_deleted",
        entity_type="receipt",
        entity_id=receipt.id,
        cassa_id=membership.cassa_id,
        user_id=membership.user_id,
        summary=f"Eliminato scontrino {receipt.filename}",
        details={"movement_id": str(movement_id)},
    )
    db.delete(receipt)
    db.commit()
