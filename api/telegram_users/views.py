from fastapi import Form, HTTPException, Depends
from deps.permissions import AdminOnly
from main import app
from core.db import get_db
from api.telegram_users import models
from sqlalchemy.orm import Session


@app.post("/telegram_user", tags=["Telegram User"])
def create_telegram_user(
    row_id           : str     = Form(...),
    telegram_user_id : str     = Form(...),
    telegram_username: str     = Form(...),
    db               : Session = Depends(get_db),
    _=AdminOnly,
):

    exists = db.query(models.Telegram_user).filter(
        models.Telegram_user.telegram_user_id == telegram_user_id
    ).first()
    if exists:
        raise HTTPException(
            status_code=409, 
            detail="telegram_user_id already exists"
        )

    new_telegram_user = models.Telegram_user(
        id                = row_id,
        telegram_user_id  = telegram_user_id,
        telegram_username = telegram_username,
    )

    db.add(new_telegram_user)
    db.commit()
    db.refresh(new_telegram_user)
    return new_telegram_user


@app.get("/telegram_user", tags=["Telegram User"])
async def get_all_tg_user(
    skip : int     = 0,
    limit: int     = 10,
    db   : Session = Depends(get_db),
    _=AdminOnly,
):
    users = db.query(models.Telegram_user).offset(skip).limit(limit).all()
    return users


@app.get("/telegram_user/{tg_user_id}", tags=["Telegram User"])
async def get_tg_user_by_id(
    tg_user_id: str,
    db        : Session = Depends(get_db),
    _=AdminOnly,
):
    user = db.query(models.Telegram_user).filter(
        models.Telegram_user.id == tg_user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404, 
            detail=f"ID {tg_user_id} not found"
        )

    return user


@app.put("/telegram_user/{tg_user_id}", tags=["Telegram User"])
async def update_tg_user(
    tg_user_id       : str,
    telegram_user_id : str | None = Form(None),
    telegram_username: str | None = Form(None),
    db               : Session = Depends(get_db),
    _=AdminOnly,
):
    user = db.query(models.Telegram_user).filter(
        models.Telegram_user.id == tg_user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404, 
            detail=f"ID {tg_user_id} not found"
        )

   
    if telegram_user_id is not None and telegram_user_id != user.telegram_user_id:
        exists = db.query(models.Telegram_user).filter(
            models.Telegram_user.telegram_user_id == telegram_user_id
        ).first()
        if exists:
            raise HTTPException(
                status_code=409, 
                detail="telegram_user_id already exists"
            )
        user.telegram_user_id = telegram_user_id


    if telegram_username is not None:
        user.telegram_username = telegram_username

    db.commit()
    db.refresh(user)
    return user


@app.delete("/telegram_user/{tg_user_id}", tags=["Telegram User"])
async def delete_tg_user(
    tg_user_id: str,
    db        : Session = Depends(get_db),
    _=AdminOnly,
):
    user = db.query(models.Telegram_user).filter(
        models.Telegram_user.id == tg_user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404, 
            detail=f"ID {tg_user_id} not found"
        )

    db.delete(user)
    db.commit()
    return {
        "message": "Delete successfully", 
        "id": tg_user_id
    }