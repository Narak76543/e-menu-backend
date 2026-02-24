from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
import os
from core.db import get_db
from main import app

from api.orders.models import OrderModel
from api.order_items.models import OrderItemModel
from api.products.models import ProductModel
from api.tables.models import TableModel
from api.public.schemas import PublicOrderDetailOut

APP_BASE_URL = os.getenv("APP_BASE_URL", "").rstrip("/")
USD_TO_KHR = float(os.getenv("USD_TO_KHR", "4000"))


def _abs_url(path: str | None) -> str | None:
    if not path:
        return None
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if APP_BASE_URL and path.startswith("/"):
        return f"{APP_BASE_URL}{path}"
    return path


@app.get("/public/orders/{order_id}", response_model=PublicOrderDetailOut, tags=["Public"])
def public_get_order(order_id: str, db: Session = Depends(get_db)):
    order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    table = db.query(TableModel).filter(TableModel.id == order.table_id).first()
    table_code = getattr(table, "code", None) or str(order.table_id)
    table_name = getattr(table, "name", None)

    items = db.query(OrderItemModel).filter(OrderItemModel.order_id == order_id).all()

    product_ids = [it.product_id for it in items]
    products = db.query(ProductModel).filter(ProductModel.id.in_(product_ids)).all() if product_ids else []
    product_map = {p.id: p for p in products}

    status_value = order.status.value if hasattr(order.status, "value") else str(order.status)

    subtotal_usd = 0.0
    item_count = 0

    out_items = []
    for it in items:
        p = product_map.get(it.product_id)

        qty = int(getattr(it, "qty", 0) or 0)
        item_count += qty

        unit_usd = float(getattr(it, "unit_price_usd", 0) or 0)
        line_usd = float(getattr(it, "line_total_usd", unit_usd * qty) or 0)

        # ✅ derive KHR from USD (single source of truth)
        unit_khr = round(unit_usd * USD_TO_KHR)
        line_khr = round(line_usd * USD_TO_KHR)

        subtotal_usd += line_usd

        out_items.append({
            "product": {
                "id": it.product_id,
                "name": getattr(it, "product_name", None) or getattr(p, "name", None),
                "name_lc": getattr(it, "product_name_lc", None) or getattr(p, "name_lc", None),
                "image_url": _abs_url(getattr(p, "image_url", None)),
            },
            "qty": qty,
            "unit_price": {"usd": unit_usd, "khr": unit_khr},
            "line_total": {"usd": line_usd, "khr": line_khr},
        })

    total_usd = float(getattr(order, "total_amount", subtotal_usd) or subtotal_usd)

    # ✅ summary KHR also derived from USD
    subtotal_khr = round(subtotal_usd * USD_TO_KHR)
    total_khr = round(total_usd * USD_TO_KHR)

    return {
        "order": {
            "id": order.id,
            "order_no": getattr(order, "order_no", None),
            "status": status_value,
            "table": {"code": table_code, "name": table_name},
            "note": getattr(order, "note", None),
            "payment": {
                "method": (getattr(order, "payment_method", None).value
                           if hasattr(getattr(order, "payment_method", None), "value")
                           else getattr(order, "payment_method", None)),
                "status": (getattr(order, "payment_status", None).value
                           if hasattr(getattr(order, "payment_status", None), "value")
                           else getattr(order, "payment_status", None)),
            },
            "created_at": getattr(order, "created_at", None),
        },
        "items": out_items,
        "summary": {
            "item_count": item_count,
            "subtotal": {"usd": subtotal_usd, "khr": subtotal_khr},
            "total": {"usd": total_usd, "khr": total_khr},
        }
    }