from datetime import datetime
from pydantic import BaseModel


class TelegramUserOut(BaseModel):
    telegram_id    : str
    username       : str | None
    first_name     : str | None
    last_name      : str | None
    last_table_code: str | None
    last_seen      : datetime | None

    class Config:
        from_attributes = True
