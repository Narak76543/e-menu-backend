from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime

from api.categories.models import CategoriesModel
from api.order_items.models import OrderItemModel
from api.orders.enums import OrderStatus
from api.orders.models import OrderModel
from api.products.models import ProductModel
from api.tables.models import TableModel
from api.telegram_users.models import Telegram_user
from core.db import get_db
from main import app

from api.public.schemas import (
    PublicCategoryOut,
    PublicProductOut,
    PublicTableOut,
    PublicOrderCreateIn,
    PublicOrderOut,
    PublicOrderDetailOut,
)



def _make_id(prefix: str) -> str:
    return f"{prefix}{uuid4().hex[:12]}"


def _make_order_no() -> str:
    return f"ORD-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:6].upper()}"


def _get_or_create_telegram_user(
    db: Session,
    telegram_username: str | None,
) -> Telegram_user:
    username = (telegram_username or "").strip()
    if username:
        user = db.query(Telegram_user).filter(Telegram_user.telegram_username == username).first()
        if user:
            return user
        new_user = Telegram_user(
            id=_make_id("TG_"),
            telegram_user_id=_make_id("U_"),
            telegram_username=username,
        )
        db.add(new_user)
        db.flush()
        return new_user

    guest_suffix = uuid4().hex[:8]
    guest_user = Telegram_user(
        id=_make_id("TG_"),
        telegram_user_id=f"GUEST_{guest_suffix}",
        telegram_username=f"guest_{guest_suffix}",
    )
    db.add(guest_user)
    db.flush()
    return guest_user


# ----------------------------
# GET /public/categories
# ----------------------------
@app.get("/public/categories", response_model=list[PublicCategoryOut], tags=["Public"])
def public_categories(
    db: Session = Depends(get_db)
    ):
    q = db.query(CategoriesModel).filter(CategoriesModel.is_active == True)
    if hasattr(CategoriesModel, "short_order"):
        q = q.order_by(CategoriesModel.short_order.asc())
    return q.all()


# ----------------------------
# GET /public/products
# Optional: ?category_id=
# ----------------------------
@app.get("/public/products", response_model=list[PublicProductOut], tags=["Public"])
def public_products(
    category_id: str | None = None, 
    db: Session = Depends(get_db)
    ):
    q = db.query(ProductModel).filter(ProductModel.is_active == True)

    if category_id:
        q = q.filter(ProductModel.category_id == category_id)

    if hasattr(ProductModel, "created_at"):
        q = q.order_by(ProductModel.created_at.desc())

    return q.all()


# ----------------------------
# GET /public/tables/{code}
# validate table
# ----------------------------
@app.get("/public/tables/{code}", response_model=PublicTableOut, tags=["Public"])
def public_table_by_code(code: str, db: Session = Depends(get_db)):
    table = db.query(TableModel).filter(TableModel.code == code).first()

    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    if not getattr(table, "is_active", True):
        raise HTTPException(status_code=403, detail="Table is inactive")

    return table


# ----------------------------
# POST /public/orders
# create order
# ----------------------------
@app.post("/public/orders", response_model=PublicOrderOut, tags=["Public"])
def public_create_order(

    payload: PublicOrderCreateIn, 
    db: Session = Depends(get_db)

    ):
    # 1) Validate table
    table = db.query(TableModel).filter(TableModel.code == payload.table_code).first()

    if not table:

        raise HTTPException(
            status_code=404, 
            detail="Invalid table code"
        )
    if not getattr(table, "is_active", True):
        raise HTTPException(
            status_code=403, 
            detail="Table is inactive"
        )

    # 2) Validate items
    if not payload.items:
        raise HTTPException(status_code=422, detail="Order items are required")

    # 3) Load products
    product_ids = [i.product_id for i in payload.items]
    products = (
        db.query(ProductModel)
        .filter(ProductModel.id.in_(product_ids))
        .filter(ProductModel.is_active == True)
        .all()
    )
    product_map = {p.id: p for p in products}

    for it in payload.items:
        if it.product_id not in product_map:
            raise HTTPException(status_code=404, detail=f"Product not found or inactive: {it.product_id}")

    # 4) Resolve telegram user (required by orders.telegram_user_id)
    tg_user = _get_or_create_telegram_user(db, payload.telegram_username)

    # 5) Create order
    new_order = OrderModel(
        id=_make_id("ODR_"),
        order_no=_make_order_no(),
        table_id=table.id,
        telegram_user_id=tg_user.id,
        status=OrderStatus.PENDING,
        note=payload.note,
        subtotal_amount=0,
        total_amount=0,
    )

    db.add(new_order)
    db.flush()  # get new_order.id

    # 6) Create items
    subtotal_usd = 0
    subtotal_khr = 0
    items_to_insert = []

    for it in payload.items:
        p = product_map[it.product_id]
        unit_price_usd = int(getattr(p, "price_usd", 0) or 0)
        unit_price_khr = int(getattr(p, "price_khr", 0) or 0)
        line_total_usd = unit_price_usd * int(it.qty)
        line_total_khr = unit_price_khr * int(it.qty)
        subtotal_usd += line_total_usd
        subtotal_khr += line_total_khr

        oi = OrderItemModel(
            id=_make_id("ITM_"),
            order_id=new_order.id,
            product_id=p.id,
            product_name=p.name,
            product_name_lc=p.name_lc,
            unit_price_usd=unit_price_usd,
            unit_price_khr=unit_price_khr,
            qty=it.qty,
            line_total_usd=line_total_usd,
            line_total_khr=line_total_khr,
        )
        items_to_insert.append(oi)

    new_order.subtotal_amount = subtotal_usd
    new_order.total_amount = subtotal_usd

    db.add_all(items_to_insert)
    db.commit()
    db.refresh(new_order)

    # 🔔 Optional: call telegram bot notify here
    # notify_kitchen(new_order.id)

    return new_order


# ----------------------------
# GET /public/orders/{id}
# order tracking
# ----------------------------
@app.get("/public/orders/{order_id}", response_model=PublicOrderDetailOut, tags=["Public"])
def public_get_order(order_id: str, db: Session = Depends(get_db)):
    order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    items = db.query(OrderItemModel).filter(OrderItemModel.order_id == order_id).all()
    product_ids = [item.product_id for item in items]
    products = db.query(ProductModel).filter(ProductModel.id.in_(product_ids)).all() if product_ids else []
    product_map = {p.id: p for p in products}

    return {
        "order": {
            "id": order.id,
            "table_id": order.table_id,
            "status": order.status.value,
            "note": order.note,
            "total_amount": order.total_amount,
        },
        "items": [
            {
                "product_id": item.product_id,
                "product_name": item.product_name,
                "product_name_lc": item.product_name_lc,
                "image_url": getattr(product_map.get(item.product_id), "image_url", None),
                "qty": item.qty,
                "price": item.unit_price_usd,
                "subtotal": item.line_total_usd,
                "price_in_khr": item.unit_price_khr,
                "subtotal_khr": item.line_total_khr,
            }
            for item in items
        ],
    }
