from fastapi import Depends, Form, HTTPException
from sqlalchemy.orm import Session
from deps.permissions import AdminOnly
from main import app
from core.db import get_db
from api.order_items import models as item_models
from api.orders import models as order_models
from api.products import models as product_models


def recalc_order_totals(db: Session, order_id: str) -> None:
    """
    Recalculate order subtotal/total from order_items.
    Here we store totals in KHR (common for KHQR).
    If you want USD totals instead, change to sum USD.
    """
    items = db.query(item_models.OrderItemModel).filter(
        item_models.OrderItemModel.order_id == order_id
    ).all()

    subtotal_khr = sum(i.line_total_khr for i in items)
    total_khr = subtotal_khr  
    order = db.query(order_models.OrderModel).filter(order_models.OrderModel.id == order_id).first()
    if order:
        order.subtotal_amount = subtotal_khr
        order.total_amount = total_khr


@app.post("/order_item", tags=["Order Item"])
async def create_order_item(
    id        : str     = Form(...),
    order_id  : str     = Form(...),
    product_id: str     = Form(...),
    qty       : int     = Form(...),
    db        : Session = Depends(get_db),
    _=AdminOnly,
):
    order = db.query(order_models.OrderModel).filter(order_models.OrderModel.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=404, 
            detail=f"Order {order_id} not found"
        )

    product = db.query(product_models.ProductModel).filter(product_models.ProductModel.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=404, 
            detail=f"Product {product_id} not found"
        )

    if hasattr(product, "is_active") and product.is_active is False:
        raise HTTPException(
            status_code=400, 
            detail="Product is inactive"
        )

    if qty <= 0:
        raise HTTPException(
            status_code=422, 
            detail="qty must be > 0"
        )

    exists = db.query(item_models.OrderItemModel).filter(item_models.OrderItemModel.id == id).first()
    if exists:
        raise HTTPException(
            status_code=409, 
            detail="Order item id already exists"
        )

    product_name    = product.name
    product_name_lc = product.name_lc
    unit_usd        = product.price_usd
    unit_khr        = product.price_khr

    new_item = item_models.OrderItemModel(
        id              = id,
        order_id        = order_id,
        product_id      = product_id,
        product_name    = product_name,
        product_name_lc = product_name_lc,
        unit_price_usd  = unit_usd,
        unit_price_khr  = unit_khr,
        qty             = qty,
        line_total_usd  = unit_usd * qty,
        line_total_khr  = unit_khr * qty,
    )

    db.add(new_item)
    recalc_order_totals(db, order_id)
    db.commit()
    db.refresh(new_item)
    return new_item

@app.get("/order_item", tags=["Order Item"])
async def get_all_order_items(
    skip    : int        = 0,
    limit   : int        = 50,
    order_id: str | None = None,
    db      : Session    = Depends(get_db),
    _=AdminOnly,
):
    q = db.query(item_models.OrderItemModel)

    if order_id:
        q = q.filter(item_models.OrderItemModel.order_id == order_id)

    items = q.offset(skip).limit(limit).all()
    return items

@app.get("/order_item/{item_id}", tags=["Order Item"])
async def get_order_item_by_id(
    item_id: str,
    db     : Session = Depends(get_db),
):
    item = db.query(item_models.OrderItemModel).filter(item_models.OrderItemModel.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=404, 
            detail=f"Item {item_id} not found"
        )
    return item

@app.put("/order_item/{item_id}", tags=["Order Item"])
async def update_order_item(
    item_id: str,
    qty    : int | None = Form(None),
    db     : Session = Depends(get_db),
    _=AdminOnly,
):
    item = db.query(item_models.OrderItemModel).filter(item_models.OrderItemModel.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=404, 
            detail=f"Item {item_id} not found"
        )

    if qty is not None:
        if qty <= 0:
            raise HTTPException(
                status_code=422, 
                detail="qty must be > 0"
            )

        item.qty = qty
        item.line_total_usd = item.unit_price_usd * qty
        item.line_total_khr = item.unit_price_khr * qty

    recalc_order_totals(db, item.order_id)
    db.commit()
    db.refresh(item)
    return item

@app.delete("/order_item/{item_id}", tags=["Order Item"])
async def delete_order_item(
    item_id: str,
    db     : Session = Depends(get_db),
    _=AdminOnly,
):
    item = db.query(item_models.OrderItemModel).filter(item_models.OrderItemModel.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=404, 
            detail=f"Item {item_id} not found"
        )

    order_id = item.order_id
    db.delete(item)
    recalc_order_totals(db, order_id)

    db.commit()
    return {
        "message": "Delete successfully", 
        "id": item_id
    }