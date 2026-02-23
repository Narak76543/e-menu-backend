from core.db import Base
from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

class Telegram_user(Base):
    __tablename__ = "tbl_telegramm_user"

    id = Column(String, primary_key=True, index=True)
    telegram_user_id = Column(String, unique=True, nullable=False)
    telegram_username = Column(String, nullable=False)

    orders = relationship("OrderModel", back_populates="telegram_user")