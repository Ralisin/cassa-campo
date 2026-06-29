from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.orm import selectinload

from app.models import (
    CampCategoryBudget,
    CampSettings,
    Cassa,
    CassaStatus,
    ExpenseCategory,
    Movement,
    MovementReimbursement,
    MovementType,
    PaymentMethod,
    TransferType,
    TreasuryTransfer,
    User,
)
from app.schemas import (
    CategorySummary,
    CassaRead,
    DashboardRead,
    MembershipRead,
    MovementInput,
    MovementRead,
    MovementReceiptRead,
    UserRead,
)

ZERO = Decimal("0.00")
CAMP_TIMEZONE = ZoneInfo("Europe/Rome")


def camp_today() -> date:
    return datetime.now(CAMP_TIMEZONE).date()


def cassa_to_read(cassa: Cassa) -> CassaRead:
    return CassaRead(
        id=cassa.id,
        group_id=cassa.group_id,
        unit=cassa.unit,
        kind=cassa.kind,
        status=cassa.status,
        year=cassa.year,
        opened_at=cassa.opened_at,
        closed_at=cassa.closed_at,
        is_closed=cassa.status == CassaStatus.CLOSED,
    )


def user_to_read(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        email=user.email,
        name=user.name,
        group_id=user.group_id,
        is_system_admin=user.is_system_admin,
        created_at=user.created_at,
        memberships=[
            MembershipRead(
                cassa_id=membership.cassa_id,
                unit=membership.cassa.unit,
                kind=membership.cassa.kind,
                status=membership.cassa.status,
                year=membership.cassa.year,
                opened_at=membership.cassa.opened_at,
                closed_at=membership.cassa.closed_at,
                is_closed=membership.cassa.status == CassaStatus.CLOSED,
                role=membership.role,
                group_id=membership.cassa.group_id,
                group_slug=membership.cassa.group.slug,
                group_name=membership.cassa.group.name,
            )
            for membership in user.memberships
        ],
    )


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


def apply_movement_input(movement: Movement, data: MovementInput, cassa: Cassa) -> None:
    for field, value in data.model_dump(exclude={"needs_reimbursement", "unit"}).items():
        setattr(movement, field, value)
    movement.cassa_id = cassa.id
    movement.unit = cassa.unit
    if data.needs_reimbursement and movement.reimbursement is None:
        movement.reimbursement = MovementReimbursement()
    elif not data.needs_reimbursement and movement.reimbursement is not None:
        movement.reimbursement = None


def get_dashboard(db: Session, cassa_id) -> DashboardRead:
    settings = db.scalar(
        select(CampSettings)
        .where(CampSettings.cassa_id == cassa_id)
        .order_by(CampSettings.created_at.desc())
        .limit(1)
    )

    def total(movement_type: MovementType, method: PaymentMethod | None = None) -> Decimal:
        query = select(func.coalesce(func.sum(Movement.amount), 0)).where(
            Movement.type == movement_type, Movement.cassa_id == cassa_id
        )
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
                TreasuryTransfer.type == TransferType.WITHDRAWAL,
                TreasuryTransfer.cassa_id == cassa_id,
            )
        )
        or 0
    )
    deposits = Decimal(
        db.scalar(
            select(func.coalesce(func.sum(TreasuryTransfer.amount), 0)).where(
                TreasuryTransfer.type == TransferType.DEPOSIT,
                TreasuryTransfer.cassa_id == cassa_id,
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
            .where(
                MovementReimbursement.reimbursed_at.is_(None),
                Movement.cassa_id == cassa_id,
            )
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
        .where(Movement.operation_date == camp_today(), Movement.cassa_id == cassa_id)
        .order_by(Movement.created_at.desc())
    ).all()
    budgets: dict[str, Decimal] = {}
    if settings:
        budgets = {
            category: amount
            for category, amount in db.execute(
                select(CampCategoryBudget.category, CampCategoryBudget.amount).where(
                    CampCategoryBudget.settings_id == settings.id
                )
            ).all()
        }
    spent_by_category = {
        category: Decimal(amount or 0)
        for category, amount in db.execute(
            select(Movement.category, func.coalesce(func.sum(Movement.amount), 0))
            .where(
                Movement.type == MovementType.EXPENSE,
                Movement.cassa_id == cassa_id,
                Movement.category.is_not(None),
            )
            .group_by(Movement.category)
        ).all()
    }
    categories = db.scalars(
        select(ExpenseCategory)
        .where(ExpenseCategory.active.is_(True))
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
            CategorySummary(
                category=category.slug,
                label=category.label,
                budget=budgets.get(category.slug, ZERO),
                spent=spent_by_category.get(category.slug, ZERO),
            )
            for category in categories
        ],
        today_movements=[movement_to_read(item) for item in today_movements],
    )
