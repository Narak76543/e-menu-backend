from pydantic import BaseModel

class TableSchema(BaseModel):
    id       : str
    code     : str
    name     : str
    is_active: bool