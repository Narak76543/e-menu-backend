from core.db import Base
from sqlalchemy import Column, String, Integer, ForeignKey


class OrderItemModel(Base):
    __tablename__ = "order_items"

    id             = Column(String, primary_key=True, index=True)
    order_id       = Column(String, ForeignKey("orders.id"), nullable=False, index=True)
    product_id     = Column(String, ForeignKey("products.id"), nullable=False, index=True)
    product_name   = Column(String, nullable=False)
    product_name_lc = Column(String, nullable=True)
    unit_price_usd = Column(Integer, nullable=False)                                        # cents
    unit_price_khr = Column(Integer, nullable=False)                                        # riel
    qty            = Column(Integer, nullable=False)
    line_total_usd = Column(Integer, nullable=False)
    line_total_khr = Column(Integer, nullable=False)