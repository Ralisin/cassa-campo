import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models import (
    BalanceType,
    Branch,
    CassaKind,
    CassaStatus,
    MovementType,
    PaymentMethod,
    TransferType,
    UserRole,
)

ExpenseCategorySlug = Literal["vitto", "alloggio", "trasporti", "varie"]


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class GroupRead(ApiModel):
    id: uuid.UUID
    slug: str
    name: str
    email_domain: str


class CassaRead(ApiModel):
    id: uuid.UUID
    group_id: uuid.UUID
    unit: Branch
    kind: CassaKind
    status: CassaStatus
    year: int
    opened_at: date
    closed_at: date | None
    is_closed: bool = False


class CassaCreate(BaseModel):
    unit: Branch
    kind: CassaKind = CassaKind.CAMPO
    year: int = Field(default_factory=lambda: date.today().year)
    opened_at: date | None = None


class MembershipRead(BaseModel):
    cassa_id: uuid.UUID
    unit: Branch
    kind: CassaKind
    status: CassaStatus
    year: int
    opened_at: date
    closed_at: date | None
    is_closed: bool
    role: UserRole
    group_id: uuid.UUID
    group_slug: str
    group_name: str


class UserRead(ApiModel):
    id: uuid.UUID
    email: EmailStr
    name: str
    group_id: uuid.UUID
    is_system_admin: bool = False
    created_at: datetime
    memberships: list[MembershipRead] = Field(default_factory=list)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=72)


class MembershipInput(BaseModel):
    unit: Branch
    kind: CassaKind = CassaKind.CAMPO
    role: UserRole = UserRole.USER


class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=72)
    memberships: list[MembershipInput] = Field(min_length=1)


class UserUpdate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=72)
    memberships: list[MembershipInput] = Field(min_length=1)


class MovementInput(BaseModel):
    operation_date: date
    type: MovementType
    payment_method: PaymentMethod
    supplier: str = Field(min_length=1, max_length=255)
    # The unit is always forced server-side to the active cassa's unit; any value
    # sent by the client is ignored.
    unit: Branch | None = None
    balance_type: BalanceType = BalanceType.CAMP
    category: ExpenseCategorySlug | None = None
    amount: Decimal = Field(gt=0, decimal_places=2)
    notes: str = Field(min_length=1)
    needs_reimbursement: bool = False

    @model_validator(mode="after")
    def validate_reimbursement(self) -> "MovementInput":
        if self.type == MovementType.EXPENSE and self.category is None:
            raise ValueError("An expense category is required")
        if self.type == MovementType.INCOME:
            self.category = None
        if self.needs_reimbursement and (
            self.type != MovementType.EXPENSE or self.payment_method != PaymentMethod.CASH
        ):
            raise ValueError("A reimbursement requires a cash expense")
        return self


class MovementReceiptRead(ApiModel):
    id: uuid.UUID
    movement_id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    created_at: datetime
    uploaded_by: uuid.UUID


class MovementRead(ApiModel):
    id: uuid.UUID
    created_at: datetime
    operation_date: date
    type: MovementType
    payment_method: PaymentMethod
    supplier: str
    unit: str
    balance_type: BalanceType
    category: str | None
    amount: Decimal
    notes: str | None
    created_by: uuid.UUID
    creator_name: str
    creator_email: EmailStr
    needs_reimbursement: bool
    reimbursement_status: str | None
    reimbursed_at: datetime | None
    reimbursed_by_name: str | None
    receipts: list[MovementReceiptRead] = Field(default_factory=list)


class MovementCreatorRead(BaseModel):
    id: uuid.UUID
    name: str


class MovementPage(BaseModel):
    items: list[MovementRead]
    next_cursor: str | None
    total: int
    creators: list[MovementCreatorRead]


class ReimbursementUpdate(BaseModel):
    reimbursed: bool


class ReimbursementSummary(BaseModel):
    pending_amount: Decimal
    reimbursed_amount: Decimal
    pending_count: int
    reimbursed_count: int
    movements: list[MovementRead]


class NotificationRead(ApiModel):
    id: uuid.UUID
    movement_id: uuid.UUID
    kind: str
    title: str
    message: str
    created_at: datetime
    read_at: datetime | None


class NotificationList(BaseModel):
    items: list[NotificationRead]
    unread_count: int


class TransferInput(BaseModel):
    operation_date: date
    type: TransferType
    amount: Decimal = Field(gt=0, decimal_places=2)
    notes: str = Field(min_length=1)


class TransferRead(ApiModel):
    id: uuid.UUID
    created_at: datetime
    operation_date: date
    type: TransferType
    amount: Decimal
    notes: str
    created_by: uuid.UUID
    creator_name: str


class SettingsInput(BaseModel):
    camp_year: int
    camp_name: str = Field(min_length=1, max_length=255)
    participants: int = Field(ge=0)
    quota_per_person: Decimal = Field(ge=0)
    cash_initial: Decimal = Field(ge=0)
    category_budgets: dict[ExpenseCategorySlug, Decimal] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_cash_initial(self) -> "SettingsInput":
        if self.cash_initial > self.participants * self.quota_per_person:
            raise ValueError("Initial cash cannot exceed the camp budget")
        if any(amount < 0 for amount in self.category_budgets.values()):
            raise ValueError("Category budgets cannot be negative")
        return self


class SettingsRead(ApiModel):
    id: uuid.UUID
    camp_year: int
    camp_name: str
    participants: int
    quota_per_person: Decimal
    max_budget: Decimal
    cash_initial: Decimal
    bank_initial: Decimal
    category_budgets: dict[str, Decimal]


class CategorySummary(BaseModel):
    category: str
    label: str
    budget: Decimal
    spent: Decimal


class DashboardRead(BaseModel):
    max_budget: Decimal
    spent: Decimal
    remaining_budget: Decimal
    cash_balance: Decimal
    pending_reimbursements: Decimal
    bank_balance: Decimal
    category_summaries: list[CategorySummary]
    today_movements: list[MovementRead]


class SystemCassaRead(ApiModel):
    id: uuid.UUID
    group_id: uuid.UUID
    unit: str
    kind: CassaKind
    status: CassaStatus
    year: int
    opened_at: date
    closed_at: date | None
    is_closed: bool = False
    created_at: datetime
    movements_count: int = 0
    cash_balance: Decimal = Decimal("0.00")
    bank_balance: Decimal = Decimal("0.00")


class SystemGroupRead(ApiModel):
    id: uuid.UUID
    slug: str
    name: str
    email_domain: str
    created_at: datetime
    users_count: int = 0
    casse: list[SystemCassaRead] = Field(default_factory=list)


class SystemOverview(BaseModel):
    groups: list[SystemGroupRead]
