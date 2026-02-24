from fastapi import Depends, Form, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from deps.permissions import AdminOnly
from main import app
from core.db import get_db
from api.orders import models as order_models
from api.orders.enums import OrderStatus, PaymentMethod, PaymentStatus
from api.tables import models as table_models
from api.telegram_users import models as tg_models


def generate_order_no(db: Session) -> str:
    """
    Format: ORD-YYYYMMDD-0001
    """
    today = datetime.utcnow().strftime("%Y%m%d")
    prefix = f"ORD-{today}-"

    last = (
        db.query(order_models.OrderModel)
        .filter(order_models.OrderModel.order_no.like(prefix + "%"))
        .order_by(order_models.OrderModel.order_no.desc())
        .first()
    )

    if not last:
        return f"{prefix}0001"

    try:
        last_seq = int(last.order_no.split("-")[-1])
    except Exception:
        last_seq = 0

    return f"{prefix}{last_seq + 1:04d}"


@app.post("/order", tags=["Order"])
async def create_order(
    id              : str           = Form(...),
    table_id        : str           = Form(...),
    telegram_user_id: str           = Form(...),
    payment_method  : PaymentMethod = Form(PaymentMethod.COD),
    note            : str | None    = Form(None),
    db              : Session       = Depends(get_db),
    _=AdminOnly,
):
    # Check table exists
    table = db.query(table_models.TableModel).filter(table_models.TableModel.id == table_id).first()
    if not table:
        raise HTTPException(
            status_code=404, 
            detail=f"Table {table_id} not found"
        )

    # Check telegram user exists
    tg_user = db.query(tg_models.Telegram_user).filter(tg_models.Telegram_user.id == telegram_user_id).first()
    if not tg_user:
        raise HTTPException(
            status_code=404, 
            detail=f"Telegram user {telegram_user_id} not found"
        )

    # Prevent duplicate id
    exists = db.query(order_models.OrderModel).filter(order_models.OrderModel.id == id).first()
    if exists:
        raise HTTPException(
            status_code=409, 
            detail="Order id already exists"
        )

    now = datetime.utcnow()
    order_no = generate_order_no(db)

    new_order = order_models.OrderModel(
        id               = id,
        order_no         = order_no,
        table_id         = table_id,
        telegram_user_id = telegram_user_id,
        status           = OrderStatus.PENDING,
        payment_method   = payment_method,
        payment_status   = PaymentStatus.UNPAID,
        subtotal_amount  = 0,
        total_amount     = 0,
        note             = note,
        created_at       = now,
        updated_at       = now,
    )

    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    return new_order


@app.get("/order", tags=["Order"])
async def get_all_orders(
    skip          : int                  = 0,
    limit         : int                  = 10,
    status        : OrderStatus | None   = None,
    payment_method: PaymentMethod | None = None,
    payment_status: PaymentStatus | None = None,
    table_id      : str | None           = None,
    db            : Session              = Depends(get_db),
    _=AdminOnly,
):
    q = db.query(order_models.OrderModel)

    if status is not None:
        q = q.filter(order_models.OrderModel.status == status)

    if payment_method is not None:
        q = q.filter(order_models.OrderModel.payment_method == payment_method)

    if payment_status is not None:
        q = q.filter(order_models.OrderModel.payment_status == payment_status)

    if table_id is not None:
        q = q.filter(order_models.OrderModel.table_id == table_id)

    orders = (
        q.order_by(order_models.OrderModel.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return orders

@app.get("/order/{order_id}", tags=["Order"])
async def get_order_by_id(
    order_id: str,
    db      : Session = Depends(get_db),
    _=AdminOnly,
):
    order = db.query(order_models.OrderModel).filter(order_models.OrderModel.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=404, 
            detail=f"Order {order_id} not found"
        )
    return order


@app.put("/order/{order_id}", tags=["Order"])
async def update_order(
    order_id       : str,
    status         : OrderStatus | None = Form(None),
    payment_method : PaymentMethod | None = Form(None),
    payment_status : PaymentStatus | None = Form(None),
    subtotal_amount: int | None = Form(None),
    total_amount   : int | None = Form(None),
    note           : str | None = Form(None),
    db             : Session = Depends(get_db),
    _=AdminOnly,
):
    order = db.query(order_models.OrderModel).filter(order_models.OrderModel.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=404, 
            detail=f"Order {order_id} not found"
        )

    if status is not None:
        order.status = status

    if payment_method is not None:
        order.payment_method = payment_method

    if payment_status is not None:
        order.payment_status = payment_status

    if subtotal_amount is not None:
        if subtotal_amount < 0:
            raise HTTPException(
                status_code=422, 
                detail="subtotal_amount must be >= 0"
            )
        order.subtotal_amount = subtotal_amount

    if total_amount is not None:
        if total_amount < 0:
            raise HTTPException(
                status_code=422, 
                detail="total_amount must be >= 0"
            )
        order.total_amount = total_amount

    if note is not None:
        order.note = note

    order.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(order)
    return order

@app.delete("/order/{order_id}", tags=["Order"])
async def delete_order(
    order_id: str,
    db: Session = Depends(get_db),
    _=AdminOnly,
):
    order = db.query(order_models.OrderModel).filter(order_models.OrderModel.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=404, 
            detail=f"Order {order_id} not found"
        )

    db.delete(order)
    db.commit()
    return {
        "message": "Delete successfully", 
        "id": order_id
    }
