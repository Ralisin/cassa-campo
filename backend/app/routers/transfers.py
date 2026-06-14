import uuid

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.dependencies import CurrentUser, DbSession, OperatorUser
from app.models import TransferType, TreasuryTransfer
from app.schemas import TransferInput, TransferRead
from app.services import get_dashboard

router = APIRouter(prefix="/transfers", tags=["transfers"])


def get_transfer_or_404(db: DbSession, transfer_id: uuid.UUID) -> TreasuryTransfer:
    transfer = db.scalar(
        select(TreasuryTransfer)
        .options(joinedload(TreasuryTransfer.creator))
        .where(TreasuryTransfer.id == transfer_id)
    )
    if not transfer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transfer not found")
    return transfer


def transfer_to_read(transfer: TreasuryTransfer) -> TransferRead:
    return TransferRead(
        id=transfer.id,
        created_at=transfer.created_at,
        operation_date=transfer.operation_date,
        type=transfer.type,
        amount=transfer.amount,
        notes=transfer.notes,
        created_by=transfer.created_by,
        creator_name=transfer.creator.name,
    )


def validate_available_balance(
    data: TransferInput, db: DbSession, existing: TreasuryTransfer | None = None
) -> None:
    dashboard = get_dashboard(db)
    cash_balance = dashboard.cash_balance
    bank_balance = dashboard.bank_balance
    if existing:
        if existing.type == TransferType.WITHDRAWAL:
            cash_balance -= existing.amount
            bank_balance += existing.amount
        else:
            cash_balance += existing.amount
            bank_balance -= existing.amount

    available = bank_balance if data.type == TransferType.WITHDRAWAL else cash_balance
    if data.amount > available:
        source = "carta" if data.type == TransferType.WITHDRAWAL else "contanti"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Saldo {source} insufficiente per il giroconto",
        )


def apply_transfer_input(transfer: TreasuryTransfer, data: TransferInput) -> None:
    transfer.operation_date = data.operation_date
    transfer.type = data.type
    transfer.amount = data.amount
    transfer.notes = data.notes.strip()


@router.get("", response_model=list[TransferRead])
def list_transfers(db: DbSession, _: CurrentUser) -> list[TransferRead]:
    transfers = db.scalars(
        select(TreasuryTransfer)
        .options(joinedload(TreasuryTransfer.creator))
        .order_by(TreasuryTransfer.operation_date.desc(), TreasuryTransfer.created_at.desc())
    ).all()
    return [transfer_to_read(transfer) for transfer in transfers]


@router.post("", response_model=TransferRead, status_code=status.HTTP_201_CREATED)
def create_transfer(data: TransferInput, db: DbSession, operator: OperatorUser) -> TransferRead:
    validate_available_balance(data, db)
    transfer = TreasuryTransfer(
        created_by=operator.id,
    )
    apply_transfer_input(transfer, data)
    db.add(transfer)
    db.commit()
    db.refresh(transfer)
    return transfer_to_read(get_transfer_or_404(db, transfer.id))


@router.put("/{transfer_id}", response_model=TransferRead)
def update_transfer(
    transfer_id: uuid.UUID, data: TransferInput, db: DbSession, _: OperatorUser
) -> TransferRead:
    transfer = get_transfer_or_404(db, transfer_id)
    validate_available_balance(data, db, existing=transfer)
    apply_transfer_input(transfer, data)
    db.commit()
    return transfer_to_read(get_transfer_or_404(db, transfer.id))


@router.delete("/{transfer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transfer(transfer_id: uuid.UUID, db: DbSession, _: OperatorUser) -> Response:
    transfer = get_transfer_or_404(db, transfer_id)
    db.delete(transfer)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
