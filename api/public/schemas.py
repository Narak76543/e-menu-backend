from pydantic import BaseModel, Field


class PublicCategoryOut(BaseModel):
    id: str
    name: str
    is_active: bool = True

    class Config:
        from_attributes = True


class PublicProductOut(BaseModel):
    id         : str
    category_id: str
    name       : str
    price      : float
    image_url  : str | None = None
    description: str | None = None
    is_active  : bool = True



class PublicTableOut(BaseModel):
    id       : str
    code     : str
    name     : str | None = None
    is_active: bool = True


class OrderItemIn(BaseModel):
    product_id: str
    qty       : int = Field(..., ge=1)


class PublicOrderCreateIn(BaseModel):
    table_code       : str
    telegram_username: str | None = None
    note             : str | None = None
    items            : list[OrderItemIn]


class PublicOrderOut(BaseModel):
    id          : str
    table_id    : str
    status      : str
    note        : str | None = None
    total_amount: float

class PublicOrderItemOut(BaseModel):
    product_id    : str
    product_name  : str
    product_name_lc: str | None = None
    image_url     : str | None = None
    qty           : int
    price         : float
    subtotal      : float
    price_in_khr  : float
    subtotal_khr  : float

class PublicOrderDetailOut(BaseModel):
    
    order: PublicOrderOut
    items: list[PublicOrderItemOut]
