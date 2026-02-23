from core.db import Base
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship

class ProductModel(Base):
    __tablename__ = "products"

    id          = Column(String, primary_key=True, index=True)
    category_id = Column(String, ForeignKey("tbl_categoies.id"), nullable=False, index=True)
    name        = Column(String, nullable=False)
    name_lc     = Column(String, nullable=True)
    price_usd   = Column(Integer, nullable=False)
    price_khr   = Column(Integer, nullable=False)
    image_url   = Column(String, nullable=True)
    is_active   = Column(Boolean, default=True, nullable=False)
    category    = relationship("CategoriesModel", back_populates="products")