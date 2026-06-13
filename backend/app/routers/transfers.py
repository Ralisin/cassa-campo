from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.dependencies import AdminUser, CurrentUser, DbSession
from app.models import TransferType, TreasuryTransfer
from app.schemas import TransferInput, TransferRead
from app.services import get_dashboard

router = APIRouter(prefix="/transfers", tags=["transfers"])


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


@router.get("", response_model=list[TransferRead])
def list_transfers(db: DbSession, _: CurrentUser) -> list[TransferRead]:
    transfers = db.scalars(
        select(TreasuryTransfer)
        .options(joinedload(TreasuryTransfer.creator))
        .order_by(TreasuryTransfer.operation_date.desc(), TreasuryTransfer.created_at.desc())
    ).all()
    return [transfer_to_read(transfer) for transfer in transfers]


@router.post("", response_model=TransferRead, status_code=status.HTTP_201_CREATED)
def create_transfer(data: TransferInput, db: DbSession, admin: AdminUser) -> TransferRead:
    dashboard = get_dashboard(db)
    available = (
        dashboard.bank_balance if data.type == TransferType.WITHDRAWAL else dashboard.cash_balance
    )
    if data.amount > available:
        source = "carta" if data.type == TransferType.WITHDRAWAL else "contanti"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Saldo {source} insufficiente per il giroconto",
        )
    transfer = TreasuryTransfer(
        operation_date=data.operation_date,
        type=data.type,
        amount=data.amount,
        notes=data.notes.strip(),
        created_by=admin.id,
    )
    db.add(transfer)
    db.commit()
    db.refresh(transfer)
    return transfer_to_read(
        db.scalar(
            select(TreasuryTransfer)
            .options(joinedload(TreasuryTransfer.creator))
            .where(TreasuryTransfer.id == transfer.id)
        )
    )
