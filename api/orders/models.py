from core.db import Base
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime

from api.orders.enums import OrderStatus, PaymentMethod, PaymentStatus


class OrderModel(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, index=True)

    order_no = Column(String, unique=True, nullable=False, index=True)

    # ✅ FIXED: match your real table names
    table_id = Column(String, ForeignKey("tbl_table.id"), nullable=False, index=True)
    telegram_user_id = Column(String, ForeignKey("tbl_telegramm_user.id"), nullable=False, index=True)

    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    payment_method = Column(Enum(PaymentMethod), default=PaymentMethod.COD, nullable=False)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.UNPAID, nullable=False)

    subtotal_amount = Column(Integer, default=0, nullable=False)
    total_amount = Column(Integer, default=0, nullable=False)

    note = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Optional relationships (recommended)
    table = relationship("TableModel", back_populates="orders")
    telegram_user = relationship("Telegram_user", back_populates="orders")