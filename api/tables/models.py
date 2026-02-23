from core.db import Base
from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship

class TableModel(Base):
    __tablename__ = "tbl_table"

    id = Column(String, primary_key=True, index=True)
    code = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False, unique=True)
    is_active = Column(Boolean, default=True)

    orders = relationship("OrderModel", back_populates="table")