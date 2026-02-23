from core.db import Base
from sqlalchemy import Column, String, Boolean, Integer
from sqlalchemy.orm import relationship

class CategoriesModel(Base):
    __tablename__ = "tbl_categoies"

    id          = Column(String, primary_key=True, index=True)
    name        = Column(String, nullable=False, unique=True)
    name_lc     = Column(String, nullable=False, unique=True)
    is_active   = Column(Boolean, default=True)
    short_order = Column(Integer)

    # ✅ THIS MUST EXIST (because ProductModel.back_populates="products")
    products = relationship("ProductModel", back_populates="category")