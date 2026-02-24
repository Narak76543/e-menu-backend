from pydantic import BaseModel


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AdminUserOut(BaseModel):
    id: int
    username: str
    full_name: str | None = None
    role: str
    is_active: bool

    class Config:
        from_attributes = True