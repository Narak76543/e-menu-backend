from pydantic import BaseModel

class TelegramUser (BaseModel):
    id : str
    telegram_user_id : str
    telegram_username : str