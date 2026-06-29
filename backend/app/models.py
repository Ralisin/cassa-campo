import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def current_year() -> int:
    return date.today().year


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    CASHIER = "cashier"
    USER = "user"


class MovementType(str, enum.Enum):
    INCOME = "entrata"
    EXPENSE = "uscita"


class PaymentMethod(str, enum.Enum):
    CASH = "contanti"
    CARD = "carta"


class BalanceType(str, enum.Enum):
    ORDINARY = "O"
    CAMP = "C"
    FUNDRAISING = "A"


class TransferType(str, enum.Enum):
    WITHDRAWAL = "prelievo"
    DEPOSIT = "versamento"


class Branch(str, enum.Enum):
    LUPETTI_COCCINELLE = "L/C"
    ESPLORATORI_GUIDE = "E/G"
    ROVER_SCOLTE = "R/S"
    COCA = "CoCa"
    GRUPPO = "Gruppo"


class CassaKind(str, enum.Enum):
    CAMPO = "campo"
    ANNO = "anno"


class CassaStatus(str, enum.Enum):
    OPEN = "aperta"
    CLOSED = "chiusa"


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    email_domain: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    users: Mapped[list["User"]] = relationship(back_populates="group")
    casse: Mapped[list["Cassa"]] = relationship(back_populates="group", cascade="all, delete-orphan")


class Cassa(Base):
    __tablename__ = "casse"
    __table_args__ = (UniqueConstraint("group_id", "unit", "kind", "year", name="uq_casse_group_unit_kind_year"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    unit: Mapped[str] = mapped_column(String(50))
    kind: Mapped[CassaKind] = mapped_column(Enum(CassaKind), default=CassaKind.CAMPO)
    status: Mapped[CassaStatus] = mapped_column(Enum(CassaStatus), default=CassaStatus.OPEN)
    year: Mapped[int] = mapped_column(default=current_year)
    opened_at: Mapped[date] = mapped_column(Date, default=date.today)
    closed_at: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    group: Mapped[Group] = relationship(back_populates="casse")
    memberships: Mapped[list["Membership"]] = relationship(
        back_populates="cassa", cascade="all, delete-orphan"
    )


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "cassa_id", name="uq_memberships_user_cassa"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    cassa_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("casse.id", ondelete="CASCADE"), index=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="memberships")
    cassa: Mapped[Cassa] = relationship(back_populates="memberships")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("groups.id"), index=True)
    is_system_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    group: Mapped[Group] = relationship(back_populates="users")
    memberships: Mapped[list["Membership"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    movements: Mapped[list["Movement"]] = relationship(back_populates="creator")
    transfers: Mapped[list["TreasuryTransfer"]] = relationship(back_populates="creator")


class CampSettings(Base):
    __tablename__ = "camp_settings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    cassa_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("casse.id", ondelete="CASCADE"), index=True)
    camp_year: Mapped[int]
    camp_name: Mapped[str] = mapped_column(String(255))
    participants: Mapped[int] = mapped_column(default=0)
    quota_per_person: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    max_budget: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    cash_initial: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    bank_initial: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    category_budgets: Mapped[list["CampCategoryBudget"]] = relationship(
        back_populates="settings", cascade="all, delete-orphan"
    )


class ExpenseCategory(Base):
    __tablename__ = "expense_categories"

    slug: Mapped[str] = mapped_column(String(50), primary_key=True)
    label: Mapped[str] = mapped_column(String(100), unique=True)
    position: Mapped[int]
    active: Mapped[bool] = mapped_column(default=True)

    movements: Mapped[list["Movement"]] = relationship(back_populates="expense_category")
    budgets: Mapped[list["CampCategoryBudget"]] = relationship(back_populates="expense_category")


class CampCategoryBudget(Base):
    __tablename__ = "camp_category_budgets"

    settings_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("camp_settings.id", ondelete="CASCADE"), primary_key=True
    )
    category: Mapped[str] = mapped_column(
        ForeignKey("expense_categories.slug"), primary_key=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)

    settings: Mapped[CampSettings] = relationship(back_populates="category_budgets")
    expense_category: Mapped[ExpenseCategory] = relationship(back_populates="budgets")


class Movement(Base):
    __tablename__ = "movements"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    cassa_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("casse.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    operation_date: Mapped[date] = mapped_column(Date)
    type: Mapped[MovementType] = mapped_column(Enum(MovementType))
    payment_method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod))
    supplier: Mapped[str] = mapped_column(String(255))
    unit: Mapped[str] = mapped_column(String(50))
    balance_type: Mapped[BalanceType] = mapped_column(
        Enum(BalanceType), default=BalanceType.CAMP
    )
    category: Mapped[str | None] = mapped_column(ForeignKey("expense_categories.slug"))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))

    creator: Mapped[User] = relationship(back_populates="movements")
    expense_category: Mapped[ExpenseCategory | None] = relationship(back_populates="movements")
    reimbursement: Mapped["MovementReimbursement | None"] = relationship(
        back_populates="movement", cascade="all, delete-orphan", uselist=False
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="movement", cascade="all, delete-orphan"
    )
    receipts: Mapped[list["MovementReceipt"]] = relationship(
        back_populates="movement",
        cascade="all, delete-orphan",
        order_by="MovementReceipt.created_at",
    )


class MovementReceipt(Base):
    __tablename__ = "movement_receipts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    movement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("movements.id", ondelete="CASCADE"), index=True
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int]
    storage_key: Mapped[str] = mapped_column(String(512), unique=True)

    movement: Mapped[Movement] = relationship(back_populates="receipts")
    uploader: Mapped[User] = relationship(foreign_keys=[uploaded_by])


class MovementReimbursement(Base):
    __tablename__ = "movement_reimbursements"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    movement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("movements.id", ondelete="CASCADE"), unique=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reimbursed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reimbursed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))

    movement: Mapped[Movement] = relationship(back_populates="reimbursement")
    reimbursed_by_user: Mapped[User | None] = relationship(foreign_keys=[reimbursed_by])


class TreasuryTransfer(Base):
    __tablename__ = "treasury_transfers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    cassa_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("casse.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    operation_date: Mapped[date] = mapped_column(Date)
    type: Mapped[TransferType] = mapped_column(Enum(TransferType))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    notes: Mapped[str] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))

    creator: Mapped[User] = relationship(back_populates="transfers")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    movement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("movements.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(foreign_keys=[user_id])
    movement: Mapped[Movement] = relationship(back_populates="notifications")
