from pydantic import BaseModel
from datetime import datetime

class Money(BaseModel):
    usd: float
    khr: float

class ProductMiniOut(BaseModel):
    id: str
    name: str | None = None
    name_lc: str | None = None
    image_url: str | None = None

class PublicOrderItemOut(BaseModel):
    product: ProductMiniOut
    qty: int
    unit_price: Money
    line_total: Money

class TableMiniOut(BaseModel):
    code: str
    name: str | None = None

class PaymentOut(BaseModel):
    method: str | None = None
    status: str | None = None

class PublicOrderHeaderOut(BaseModel):
    id: str
    order_no: str | None = None
    status: str
    table: TableMiniOut
    note: str | None = None
    payment: PaymentOut
    created_at: datetime | None = None

class PublicOrderSummaryOut(BaseModel):
    item_count: int
    subtotal: Money
    total: Money

class PublicOrderDetailOut(BaseModel):
    order: PublicOrderHeaderOut
    items: list[PublicOrderItemOut]
    summary: PublicOrderSummaryOut