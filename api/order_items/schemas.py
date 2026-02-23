from pydantic import BaseModel, Field
from typing import Optional


# -------------------------
# Base Schema
# -------------------------
class OrderItemBase(BaseModel):
    order_id: str = Field(..., min_length=1)
    product_id: str = Field(..., min_length=1)

    product_name: str = Field(..., min_length=1)

    unit_price_usd: int = Field(..., ge=0)
    unit_price_khr: int = Field(..., ge=0)

    qty: int = Field(..., gt=0)

    line_total_usd: int = Field(..., ge=0)
    line_total_khr: int = Field(..., ge=0)


# -------------------------
# Create
# -------------------------
class OrderItemCreate(BaseModel):
    id: str = Field(..., min_length=1)
    order_id: str = Field(..., min_length=1)
    product_id: str = Field(..., min_length=1)
    qty: int = Field(..., gt=0)


# -------------------------
# Update (only qty allowed)
# -------------------------
class OrderItemUpdate(BaseModel):
    qty: Optional[int] = Field(None, gt=0)