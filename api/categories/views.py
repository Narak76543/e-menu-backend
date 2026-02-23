from fastapi import Depends, Form, HTTPException
from sqlalchemy.orm import Session

from api.categories import models
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


@app.post("/category", tags=["Category"])
async def create_category(
    id         : str        = Form(...),
    name       : str        = Form(...),
    name_lc    : str | None = Form(None),
    is_active  : str | None = Form(None),
    short_order: int        = Form(...),
    db         : Session    = Depends(get_db),
):
    exists = db.query(models.CategoriesModel).filter(models.CategoriesModel.name == name).first()
    if exists:
        raise HTTPException(
            status_code=409, 
            detail="Category name already exists"
        )

    new_category = models.CategoriesModel(
        id          = id,
        name        = name,
        name_lc     = name_lc,
        is_active   = parse_bool(is_active) if is_active is not None else True,
        short_order = short_order,
    )

    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category

@app.get("/category", tags=["Category"])
async def get_all_category(
    skip : int     = 0,
    limit: int     = 10,
    db   : Session = Depends(get_db),
):
    categories = (
        db.query(models.CategoriesModel)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return categories

@app.get("/category/{category_id}", tags=["Category"])
async def get_category_by_id(
    category_id: str,
    db         : Session = Depends(get_db),
):
    category = db.query(models.CategoriesModel).filter(models.CategoriesModel.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=404, 
            detail=f"ID {category_id} not found"
        )
    return category

@app.put("/category/{category_id}", tags=["Category"])
async def update_category(
    category_id: str,
    name       : str | None = Form(None),
    name_lc    : str | None = Form(None),
    is_active  : str | None = Form(None),
    short_order: int | None = Form(None),
    db         : Session = Depends(get_db),
):
    category = db.query(models.CategoriesModel).filter(models.CategoriesModel.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=404, 
            detail=f"ID {category_id} not found"
        )

    if name is not None and name != category.name:
        exists = db.query(models.CategoriesModel).filter(models.CategoriesModel.name == name).first()
        if exists:
            raise HTTPException(
                status_code=409, 
                detail="Category name already exists"
            )
        category.name = name

    if name_lc is not None:
        category.name_lc = name_lc

    if short_order is not None:
        category.short_order = short_order

    if is_active is not None:
        parsed = parse_bool(is_active)
        if parsed is None:
            raise HTTPException(
                status_code=422, 
                detail="is_active must be true/false"
            )
        category.is_active = parsed

    db.commit()
    db.refresh(category)
    return category

@app.delete("/category/{category_id}", tags=["Category"])
async def delete_category(
    category_id: str,
    db         : Session = Depends(get_db),
):
    category = db.query(models.CategoriesModel).filter(models.CategoriesModel.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=404, 
            detail=f"ID {category_id} not found"
        )

    db.delete(category)
    db.commit()
    return {
        "message": "Delete successfully", 
        "id": category_id
    }