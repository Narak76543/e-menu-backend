import os
import uuid
import shutil
from typing import Optional
from fastapi import Depends, Form, HTTPException, UploadFile, File, Request
from sqlalchemy.orm import Session
from api.products import models
from api.categories import models as category_models
from core.db import get_db
from main import app


UPLOAD_DIR = "static/images"
os.makedirs(UPLOAD_DIR, exist_ok=True)


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


def save_upload_image(image: UploadFile) -> str:

    allowed = {"image/jpeg", "image/png", "image/webp"}
    if image.content_type not in allowed:
        raise HTTPException(
            status_code=400, 
            detail="Only jpg/png/webp images are allowed"
        )

    ext = (image.filename or "").split(".")[-1].lower() if image.filename else "jpg"
    if ext not in ("jpg", "jpeg", "png", "webp"):
        # fallback based on content type
        ext = "jpg"

    filename = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    return f"/static/images/{filename}"


def delete_image_file(image_url: Optional[str]) -> None:
    """
    Delete saved image file from disk if exists.
    image_url example: /static/images/xxx.jpg
    """
    if not image_url:
        return

    local_path = image_url.lstrip("/")
    if os.path.exists(local_path) and os.path.isfile(local_path):
        try:
            os.remove(local_path)
        except Exception:
            pass


def to_public_url(request: Request, path: Optional[str]) -> Optional[str]:

    if not path:
        return None
    base = str(request.base_url).rstrip("/")
    if path.startswith("/"):
        return base + path
    return base + "/" + path


def product_to_dict(request: Request, p) -> dict:
    """
    Return clean JSON dict and convert image_url to full URL.
    """
    return {
        "id": p.id,
        "category_id": p.category_id,
        "name": p.name,
        "name_lc": p.name_lc,
        "price_usd": p.price_usd,
        "price_khr": p.price_khr,
        "is_active": p.is_active,
        "image_url": to_public_url(request, p.image_url),
    }


@app.post("/product", tags=["Product"])
async def create_product(
    request    : Request,
    id         : str = Form(...),
    category_id: str = Form(...),
    name       : str = Form(...),
    name_lc    : str | None = Form(None),
    price_usd  : int = Form(...),
    price_khr  : int = Form(...),
    is_active  : str | None = Form(None),
    image      : UploadFile | None = File(None),
    db         : Session = Depends(get_db),
):

    category = db.query(category_models.CategoriesModel).filter(
        category_models.CategoriesModel.id == category_id
    ).first()
    if not category:
        raise HTTPException(
            status_code=404, 
            detail=f"Category {category_id} not found"
        )


    exists = db.query(models.ProductModel).filter(models.ProductModel.id == id).first()
    if exists:
        raise HTTPException(
            status_code=409, 
            detail="Product id already exists"
        )

    if price_usd < 0 or price_khr < 0:
        raise HTTPException(
            status_code=422, 
            detail="Price must be >= 0"
        )

    image_url = None
    if image:
        image_url = save_upload_image(image)

    new_product = models.ProductModel(
        id          = id,
        category_id = category_id,
        name        = name,
        name_lc     = name_lc,
        price_usd   = price_usd,
        price_khr   = price_khr,
        image_url   = image_url,
        is_active   = parse_bool(is_active) if is_active is not None else True,
    )

    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return product_to_dict(request, new_product)


@app.get("/product", tags=["Product"])
async def get_all_products(
    request    : Request,
    skip       : int = 0,
    limit      : int = 10,
    category_id: str | None = None,
    is_active  : bool | None = None,
    db         : Session = Depends(get_db),
):
    q = db.query(models.ProductModel)

    if category_id:
        q = q.filter(models.ProductModel.category_id == category_id)

    if is_active is not None:
        q = q.filter(models.ProductModel.is_active == is_active)

    products = q.offset(skip).limit(limit).all()
    return [product_to_dict(request, p) for p in products]


@app.get("/product/{product_id}", tags=["Product"])
async def get_product_by_id(
    request   : Request,
    product_id: str,
    db        : Session = Depends(get_db),
):
    product = db.query(models.ProductModel).filter(models.ProductModel.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=404, 
            detail=f"ID {product_id} not found"
        )
    return product_to_dict(request, product)


@app.put("/product/{product_id}", tags=["Product"])
async def update_product(
    request    : Request,
    product_id : str,
    category_id: str | None = Form(None),
    name       : str | None = Form(None),
    name_lc    : str | None = Form(None),
    price_usd  : int | None = Form(None),
    price_khr  : int | None = Form(None),
    is_active  : str | None = Form(None),
    image      : UploadFile | None = File(None),
    db         : Session = Depends(get_db),
):
    product = db.query(models.ProductModel).filter(models.ProductModel.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=404, 
            detail=f"{product_id} not found"
        )

    if category_id is not None and category_id != product.category_id:
        category = db.query(category_models.CategoriesModel).filter(
            category_models.CategoriesModel.id == category_id
        ).first()
        if not category:
            raise HTTPException(
                status_code=404, 
                detail=f"Category {category_id} not found"
            )
        product.category_id = category_id

    if name is not None:
        product.name = name

    if name_lc is not None:
        product.name_lc = name_lc

    if price_usd is not None:
        if price_usd < 0:
            raise HTTPException(
                status_code=422, 
                detail="price_usd must be >= 0"
            )
        product.price_usd = price_usd

    if price_khr is not None:
        if price_khr < 0:
            raise HTTPException(
                status_code=422, 
                detail="price_khr must be >= 0"
            )
        product.price_khr = price_khr

    if is_active is not None:
        parsed = parse_bool(is_active)
        if parsed is None:
            raise HTTPException(
                status_code=422, 
                detail="is_active must be true/false"
            )
        product.is_active = parsed

    if image:
        old = product.image_url
        product.image_url = save_upload_image(image)
        delete_image_file(old)

    db.commit()
    db.refresh(product)
    return product_to_dict(request, product)

@app.delete("/product/{product_id}", tags=["Product"])
async def delete_product(
    product_id: str,
    db: Session = Depends(get_db),
):
    product = db.query(models.ProductModel).filter(models.ProductModel.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=404, 
            detail=f"{product_id} not found"
        )

    delete_image_file(product.image_url)

    db.delete(product)
    db.commit()
    return {
        "message": "Delete successfully", 
        "id": product_id
        }