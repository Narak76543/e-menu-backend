from pydantic import BaseModel


class CategoryModel(BaseModel):
    id: str
    name: str
    name_lc: str
    is_active: bool
    short_order: int

    class Config:
        from_attributes = True
