from deps.auth import require_role
from deps.permissions import AdminOnly
from fastapi import Depends, Form, HTTPException
from sqlalchemy.orm import Session

from api.tables import models
from core.db import get_db
from main import app


def parse_bool(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return value

    v = str(value).strip().lower()
    if v in ("true", "1", "on", "yes"):
        return True
    if v in ("false", "0", "off", "no"):
        return False
    return None

@app.post("/table", tags=["Table"])
async def create_table(
    id       : str        = Form(...),
    code     : str        = Form(...),
    name     : str | None = Form(None),
    is_active: str | None = Form(None),
    db       : Session    = Depends(get_db),
    _=AdminOnly,
):

    exists = db.query(models.TableModel).filter(models.TableModel.code == code).first()
    if exists:
        raise HTTPException(
            status_code=409, 
            detail="Table code already exists"
        )

    new_table = models.TableModel(
        id        = id,
        code      = code,
        name      = name,
        is_active = parse_bool(is_active) if is_active is not None else True,
    )

    db.add(new_table)
    db.commit()
    db.refresh(new_table)
    return new_table

@app.get("/table", tags=["Table"])
async def get_all_table(
    skip : int     = 0,
    limit: int     = 10,
    db   : Session = Depends(get_db),
    _=AdminOnly,
):
    tables = db.query(models.TableModel).offset(skip).limit(limit).all()
    return tables


@app.get("/table/{table_id}", tags=["Table"])
async def get_table_by_id(
    table_id: str,
    db      : Session = Depends(get_db),
):
    table = db.query(models.TableModel).filter(models.TableModel.id == table_id).first()
    if not table:
        raise HTTPException(
            status_code=404, 
            detail=f"ID {table_id} not found"
        )
    return table

@app.put("/table/{table_id}", tags=["Table"])
async def update_table(
    table_id : str,
    code     : str | None = Form(None),
    name     : str | None = Form(None),
    is_active: str | None = Form(None),
    db       : Session = Depends(get_db),
    _=AdminOnly,
):
    table = db.query(models.TableModel).filter(models.TableModel.id == table_id).first()
    if not table:
        raise HTTPException(
            status_code=404, 
            detail=f"{table_id} not found"
        )

    if code is not None and code != table.code:
        exists = db.query(models.TableModel).filter(models.TableModel.code == code).first()
        if exists:
            raise HTTPException(
                status_code=409, 
                detail="Table code already exists"
            )
        table.code = code

    if name is not None:
        table.name = name

    if is_active is not None:
        parsed = parse_bool(is_active)
        if parsed is None:
            raise HTTPException(
                status_code=422, 
                detail="is_active must be true/false"
            )
        table.is_active = parsed

    db.commit()
    db.refresh(table)
    return table


@app.delete("/table/{table_id}", tags=["Table"])
async def delete_table(
    table_id: str,
    db      : Session = Depends(get_db),
    _=AdminOnly,
):
    table = db.query(models.TableModel).filter(models.TableModel.id == table_id).first()
    if not table:
        raise HTTPException(
            status_code=404, 
            detail=f"{table_id} not found"
        )

    db.delete(table)
    db.commit()
    return {
        "message": "Delete successfully", 
        "id": table_id
    }