from pydantic import BaseModel
from sqlalchemy.orm import relationship

class CategoryModel (BaseModel):
    id         : str
    name       : str
    name_lc    : str
    is_active  : bool
    short_order: int
    
    products = relationship(
        "ProductModel",
        back_populates="category",
        cascade="all, delete"
    )