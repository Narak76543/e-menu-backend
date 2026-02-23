from pydantic import BaseModel, Field
from typing import Optional
from api.orders.enums import OrderStatus, PaymentMethod, PaymentStatus


class OrderBase(BaseModel):
    table_id: str = Field(..., min_length=1)
    telegram_user_id: str = Field(..., min_length=1)

    status: OrderStatus = OrderStatus.PENDING
    payment_method: PaymentMethod = PaymentMethod.COD
    payment_status: PaymentStatus = PaymentStatus.UNPAID

    subtotal_amount: int = Field(0, ge=0)
    total_amount: int = Field(0, ge=0)

    note: Optional[str] = None


class OrderCreate(OrderBase):
    id: str = Field(..., min_length=1)


class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    payment_method: Optional[PaymentMethod] = None
    payment_status: Optional[PaymentStatus] = None

    subtotal_amount: Optional[int] = Field(None, ge=0)
    total_amount: Optional[int] = Field(None, ge=0)

    note: Optional[str] = None