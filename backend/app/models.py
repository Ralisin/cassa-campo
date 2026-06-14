import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


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


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER)
    branch: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    movements: Mapped[list["Movement"]] = relationship(back_populates="creator")
    transfers: Mapped[list["TreasuryTransfer"]] = relationship(back_populates="creator")


class CampSettings(Base):
    __tablename__ = "camp_settings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    camp_year: Mapped[int]
    camp_name: Mapped[str] = mapped_column(String(255))
    participants: Mapped[int] = mapped_column(default=0)
    quota_per_person: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    max_budget: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    cash_initial: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    bank_initial: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Movement(Base):
    __tablename__ = "movements"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    operation_date: Mapped[date] = mapped_column(Date)
    type: Mapped[MovementType] = mapped_column(Enum(MovementType))
    payment_method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod))
    supplier: Mapped[str] = mapped_column(String(255))
    unit: Mapped[str] = mapped_column(String(50))
    balance_type: Mapped[BalanceType] = mapped_column(
        Enum(BalanceType), default=BalanceType.CAMP
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))

    creator: Mapped[User] = relationship(back_populates="movements")
    reimbursement: Mapped["MovementReimbursement | None"] = relationship(
        back_populates="movement", cascade="all, delete-orphan", uselist=False
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="movement", cascade="all, delete-orphan"
    )


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
