import os
import re
from urllib.parse import quote

from ..common.parsing import parse_bool
from deps.permissions import AdminOnly
from fastapi import Depends, Form, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from api.tables import models
from core.db import get_db
from main import app

QR_SUBDIR = os.path.join("images", "table_qr")
QR_DIR = os.path.join("static", QR_SUBDIR)


def _bot_username() -> str:
    username = os.getenv("TELEGRAM_BOT_USERNAME", "").strip()
    if username.startswith("@"):
        username = username[1:]
    return username


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", value.strip())
    return cleaned or "table"


def _table_qr_filename(table_code: str) -> str:
    return f"{_safe_filename(table_code)}.png"


def _table_qr_file_path(table_code: str) -> str:
    return os.path.join(QR_DIR, _table_qr_filename(table_code))


def _table_qr_public_url(table_code: str) -> str:
    return f"/static/{QR_SUBDIR}/{_table_qr_filename(table_code)}"


def build_telegram_start_url(table_code: str) -> str | None:
    username = _bot_username()
    if not username:
        return None
    return f"https://t.me/{username}?start={quote(table_code, safe='')}"


def build_table_qr_url(table_code: str) -> str | None:
    start_url = build_telegram_start_url(table_code)
    if not start_url:
        return None
    return _table_qr_public_url(table_code)


def ensure_table_qr_image(table_code: str) -> tuple[str, str]:
    start_url = build_telegram_start_url(table_code)
    if not start_url:
        raise HTTPException(
            status_code=400,
            detail="TELEGRAM_BOT_USERNAME is required to generate table QR",
        )

    try:
        import qrcode
    except ModuleNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail="Missing dependency: qrcode. Install with `pip install qrcode[pil]`.",
        ) from exc

    os.makedirs(QR_DIR, exist_ok=True)
    file_path = _table_qr_file_path(table_code)
    if not os.path.exists(file_path):
        img = qrcode.make(start_url)
        img.save(file_path)

    return file_path, _table_qr_public_url(table_code)


def serialize_table_with_qr(table: models.TableModel) -> dict:
    _, qr_public_url = ensure_table_qr_image(table.code)
    return {
        "id": table.id,
        "code": table.code,
        "name": table.name,
        "is_active": table.is_active,
        "telegram_start_url": build_telegram_start_url(table.code),
        "qr_code_url": qr_public_url,
    }


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
    return serialize_table_with_qr(new_table)

@app.get("/table", tags=["Table"])
async def get_all_table(
    skip : int     = 0,
    limit: int     = 10,
    db   : Session = Depends(get_db),
    _=AdminOnly,
):
    tables = db.query(models.TableModel).offset(skip).limit(limit).all()
    return [serialize_table_with_qr(table) for table in tables]


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
    return serialize_table_with_qr(table)

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
    return serialize_table_with_qr(table)


@app.get("/table/{table_id}/qr", tags=["Table"])
async def get_table_qr(
    table_id: str,
    db: Session = Depends(get_db),
):
    table = db.query(models.TableModel).filter(models.TableModel.id == table_id).first()
    if not table:
        raise HTTPException(
            status_code=404,
            detail=f"{table_id} not found"
        )
    _, qr_public_url = ensure_table_qr_image(table.code)
    return {
        "table_id": table.id,
        "table_code": table.code,
        "telegram_start_url": build_telegram_start_url(table.code),
        "qr_code_url": qr_public_url,
    }

@app.get("/table/{table_id}/qr/image", tags=["Table"])
async def get_table_qr_image(
    table_id: str,
    db: Session = Depends(get_db),
):
    table = db.query(models.TableModel).filter(models.TableModel.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail=f"{table_id} not found")

    file_path, _ = ensure_table_qr_image(table.code)
    return FileResponse(path=file_path, media_type="image/png", filename=_table_qr_filename(table.code))


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
