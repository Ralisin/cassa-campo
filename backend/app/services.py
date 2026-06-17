from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.orm import selectinload

from app.models import (
    CampCategoryBudget,
    CampSettings,
    ExpenseCategory,
    Movement,
    MovementReimbursement,
    MovementType,
    PaymentMethod,
    TransferType,
    TreasuryTransfer,
    User,
    UserRole,
)
from app.schemas import CategorySummary, DashboardRead, MovementInput, MovementRead, MovementReceiptRead

ZERO = Decimal("0.00")
CAMP_TIMEZONE = ZoneInfo("Europe/Rome")


def camp_today() -> date:
    return datetime.now(CAMP_TIMEZONE).date()


def movement_to_read(movement: Movement) -> MovementRead:
    reimbursement = movement.reimbursement
    return MovementRead(
        id=movement.id,
        created_at=movement.created_at,
        operation_date=movement.operation_date,
        type=movement.type,
        payment_method=movement.payment_method,
        supplier=movement.supplier,
        unit=movement.unit,
        balance_type=movement.balance_type,
        category=movement.category,
        amount=movement.amount,
        notes=movement.notes,
        created_by=movement.created_by,
        creator_name=movement.creator.name,
        creator_email=movement.creator.email,
        needs_reimbursement=reimbursement is not None,
        reimbursement_status=(
            "rimborsato" if reimbursement and reimbursement.reimbursed_at else "da_rimborsare"
        )
        if reimbursement
        else None,
        reimbursed_at=reimbursement.reimbursed_at if reimbursement else None,
        reimbursed_by_name=(
            reimbursement.reimbursed_by_user.name
            if reimbursement and reimbursement.reimbursed_by_user
            else None
        ),
        receipts=[MovementReceiptRead.model_validate(receipt) for receipt in movement.receipts],
    )


def apply_movement_input(movement: Movement, data: MovementInput) -> None:
    for field, value in data.model_dump(exclude={"needs_reimbursement"}).items():
        setattr(movement, field, value)
    if data.needs_reimbursement and movement.reimbursement is None:
        movement.reimbursement = MovementReimbursement()
    elif not data.needs_reimbursement and movement.reimbursement is not None:
        movement.reimbursement = None


def enforce_user_branch(data: MovementInput, user: User) -> None:
    if user.role not in (UserRole.ADMIN, UserRole.CASHIER):
        data.unit = user.branch


def get_dashboard(db: Session) -> DashboardRead:
    settings = db.scalar(select(CampSettings).order_by(CampSettings.created_at.desc()).limit(1))

    def total(movement_type: MovementType, method: PaymentMethod | None = None) -> Decimal:
        query = select(func.coalesce(func.sum(Movement.amount), 0)).where(Movement.type == movement_type)
        if method:
            query = query.where(Movement.payment_method == method)
        return Decimal(db.scalar(query) or 0)

    spent = total(MovementType.EXPENSE)
    max_budget = (
        Decimal(settings.participants) * settings.quota_per_person if settings else ZERO
    )
    cash_initial = settings.cash_initial if settings else ZERO
    bank_initial = max_budget - cash_initial
    withdrawals = Decimal(
        db.scalar(
            select(func.coalesce(func.sum(TreasuryTransfer.amount), 0)).where(
                TreasuryTransfer.type == TransferType.WITHDRAWAL
            )
        )
        or 0
    )
    deposits = Decimal(
        db.scalar(
            select(func.coalesce(func.sum(TreasuryTransfer.amount), 0)).where(
                TreasuryTransfer.type == TransferType.DEPOSIT
            )
        )
        or 0
    )
    cash_balance = (
        cash_initial
        + total(MovementType.INCOME, PaymentMethod.CASH)
        - total(MovementType.EXPENSE, PaymentMethod.CASH)
        + withdrawals
        - deposits
    )
    bank_balance = (
        bank_initial
        + total(MovementType.INCOME, PaymentMethod.CARD)
        - total(MovementType.EXPENSE, PaymentMethod.CARD)
        - withdrawals
        + deposits
    )
    pending_reimbursements = Decimal(
        db.scalar(
            select(func.coalesce(func.sum(Movement.amount), 0))
            .join(Movement.reimbursement)
            .where(MovementReimbursement.reimbursed_at.is_(None))
        )
        or 0
    )
    today_movements = db.scalars(
        select(Movement)
        .options(
            joinedload(Movement.reimbursement).joinedload(MovementReimbursement.reimbursed_by_user),
            joinedload(Movement.creator),
            selectinload(Movement.receipts),
        )
        .where(Movement.operation_date == camp_today())
        .order_by(Movement.created_at.desc())
    ).all()
    category_rows = db.execute(
        select(
            ExpenseCategory.slug,
            ExpenseCategory.label,
            func.coalesce(CampCategoryBudget.amount, 0),
            func.coalesce(func.sum(Movement.amount), 0),
        )
        .outerjoin(
            CampCategoryBudget,
            (CampCategoryBudget.category == ExpenseCategory.slug)
            & (CampCategoryBudget.settings_id == settings.id if settings else False),
        )
        .outerjoin(
            Movement,
            (Movement.category == ExpenseCategory.slug) & (Movement.type == MovementType.EXPENSE),
        )
        .where(ExpenseCategory.active.is_(True))
        .group_by(
            ExpenseCategory.slug,
            ExpenseCategory.label,
            ExpenseCategory.position,
            CampCategoryBudget.amount,
        )
        .order_by(ExpenseCategory.position)
    ).all()
    return DashboardRead(
        max_budget=max_budget,
        spent=spent,
        remaining_budget=max_budget - spent,
        cash_balance=cash_balance,
        pending_reimbursements=pending_reimbursements,
        bank_balance=bank_balance,
        category_summaries=[
            CategorySummary(category=slug, label=label, budget=budget, spent=category_spent)
            for slug, label, budget, category_spent in category_rows
        ],
        today_movements=[movement_to_read(item) for item in today_movements],
    )
