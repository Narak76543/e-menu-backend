from sqlalchemy import Column, String, DateTime, func
from core.db import Base


class TelegramUserModel(Base):
    __tablename__ = "telegram_users"

    telegram_id     = Column(String, primary_key=True, index=True)
    username        = Column(String, nullable=True)
    first_name      = Column(String, nullable=True)
    last_name       = Column(String, nullable=True)
    last_table_code = Column(String, nullable=True)
    created_at      = Column(DateTime, server_default=func.now(), nullable=False)
    last_seen       = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)