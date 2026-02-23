from decimal import Decimal
from pydantic import BaseModel, Field, field_serializer, field_validator
from typing import Optional

class ProductBase(BaseModel):
    category_id: str           = Field(..., min_length=1)
    name       : str           = Field(..., min_length=1)
    name_lc    : Optional[str] = None
    price_usd  : Decimal       = Field(..., ge=0)
    price_khr  : int           = Field(..., ge=0)
    
    image_url: Optional[str] = None
    is_active: bool          = True

    @field_validator("price_usd", mode="before")
    @classmethod
    def validate_usd(cls, v): 
        return Decimal(v).quantize(Decimal("0.01"))

    @field_serializer("price_usd")
    def serialize_price(self, price: Decimal, _info):
        return f"{price:.2f}"