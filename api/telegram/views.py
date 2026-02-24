import os
from typing import Any

import httpx
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from api.orders.enums import OrderStatus
from api.orders.models import OrderModel
from api.telegram.schemas import TelegramUserOut
from core.db import get_db
from deps.permissions import AdminOnly
from main import app

from .models import TelegramUserModel
from .services import notify_kitchen_user_ping

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
KITCHEN_CHAT_ID = os.getenv("KITCHEN_CHAT_ID", "")
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

TELEGRAM_WEBHOOK_URL = os.getenv("TELEGRAM_WEBHOOK_URL", "").strip()
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()
TELEGRAM_AUTO_SET_WEBHOOK = (
    os.getenv("TELEGRAM_AUTO_SET_WEBHOOK", "false").strip().lower() in {"1", "true", "yes", "on"}
)


def _resolved_webhook_url() -> str:
    if TELEGRAM_WEBHOOK_URL:
        return TELEGRAM_WEBHOOK_URL

    app_base_url = os.getenv("APP_BASE_URL", "").strip()
    if app_base_url:
        return f"{app_base_url.rstrip('/')}/telegram/webhook"

    return ""


async def tg_post(method: str, payload: dict) -> dict:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN missing in env")

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(f"{TG_API}/{method}", json=payload)
        response.raise_for_status()
        return response.json()


async def send_message(chat_id: str, text: str, reply_markup: dict | None = None) -> dict:
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return await tg_post("sendMessage", payload)


async def answer_callback(callback_query_id: str, text: str = "OK") -> dict:
    return await tg_post(
        "answerCallbackQuery",
        {"callback_query_id": callback_query_id, "text": text, "show_alert": False},
    )


async def edit_message(chat_id: str, message_id: int, text: str, reply_markup: dict | None = None) -> dict:
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "HTML"}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    return await tg_post("editMessageText", payload)


def build_order_keyboard(order_id: str) -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": "Accept", "callback_data": f"order:accept:{order_id}"},
                {"text": "Cancel", "callback_data": f"order:cancel:{order_id}"},
            ]
        ]
    }


def format_order_message(order: Any, items: list[Any], table_code: str) -> str:
    lines = []
    lines.append("<b>New Order</b>")
    lines.append(f"Order ID: <code>{order.id}</code>")
    lines.append(f"Table: <b>{table_code}</b>")

    note = getattr(order, "note", None)
    if note:
        lines.append(f"Note: <i>{note}</i>")

    lines.append("")
    lines.append("<b>Items</b>")

    total = 0.0
    for item in items:
        qty = int(getattr(item, "qty", 1) or 1)
        subtotal = float(getattr(item, "subtotal", 0) or 0)
        price = float(getattr(item, "price", 0) or 0)
        total += subtotal
        lines.append(f"- <code>{item.product_id}</code> x{qty} ({price:.2f}) = <b>{subtotal:.2f}</b>")

    lines.append("")
    lines.append(f"Total: <b>{float(getattr(order, 'total_amount', total) or total):.2f}</b>")
    return "\n".join(lines)


async def notify_kitchen_new_order(order: Any, items: list[Any], table_code: str) -> None:
    if not KITCHEN_CHAT_ID:
        print("KITCHEN_CHAT_ID missing; skip notify")
        return

    text = format_order_message(order, items, table_code)
    keyboard = build_order_keyboard(str(order.id))
    await send_message(KITCHEN_CHAT_ID, text, reply_markup=keyboard)


async def set_telegram_webhook() -> dict:
    webhook_url = _resolved_webhook_url()
    if not webhook_url:
        raise RuntimeError("Missing TELEGRAM_WEBHOOK_URL or APP_BASE_URL")

    payload: dict[str, Any] = {"url": webhook_url}
    if TELEGRAM_WEBHOOK_SECRET:
        payload["secret_token"] = TELEGRAM_WEBHOOK_SECRET
    return await tg_post("setWebhook", payload)


async def _handle_start_command(message: dict, db: Session) -> None:
    text = (message.get("text") or "").strip()
    if not text.startswith("/start"):
        return

    from_user = message.get("from") or {}
    telegram_id = str(from_user.get("id") or "")
    if not telegram_id:
        return

    table_code = None
    parts = text.split(maxsplit=1)
    if len(parts) == 2:
        table_code = parts[1].strip() or None

    user = db.query(TelegramUserModel).filter(TelegramUserModel.telegram_id == telegram_id).first()
    if not user:
        user = TelegramUserModel(telegram_id=telegram_id)
        db.add(user)

    user.username = from_user.get("username")
    user.first_name = from_user.get("first_name")
    user.last_name = from_user.get("last_name")
    if table_code:
        user.last_table_code = table_code
    db.commit()

    chat_id = str((message.get("chat") or {}).get("id") or telegram_id)
    if table_code:
        await send_message(chat_id, f"Table linked: <b>{table_code}</b>")
    else:
        await send_message(chat_id, "Welcome. Use /start <table_code> to link your table.")


async def _handle_order_callback(callback: dict, db: Session) -> None:
    data = callback.get("data") or ""
    callback_id = callback.get("id")
    message = callback.get("message") or {}
    chat_id = str((message.get("chat") or {}).get("id") or "")
    message_id = message.get("message_id")

    if not data.startswith("order:"):
        if callback_id:
            await answer_callback(str(callback_id), "Unsupported action")
        return

    parts = data.split(":")
    if len(parts) != 3:
        if callback_id:
            await answer_callback(str(callback_id), "Invalid action format")
        return

    _, action, order_id = parts
    order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    if not order:
        if callback_id:
            await answer_callback(str(callback_id), "Order not found")
        return

    if action == "accept":
        order.status = OrderStatus.ACCEPTED
        status_text = "ACCEPTED"
    elif action == "cancel":
        order.status = OrderStatus.CANCELLED
        status_text = "CANCELLED"
    else:
        if callback_id:
            await answer_callback(str(callback_id), "Unknown action")
        return

    db.commit()

    if callback_id:
        await answer_callback(str(callback_id), f"Order {status_text}")

    if chat_id and isinstance(message_id, int):
        current_text = (message.get("text") or "").strip()
        if current_text:
            await edit_message(chat_id, message_id, f"{current_text}\n\nStatus: <b>{status_text}</b>")


@app.on_event("startup")
async def init_telegram_webhook() -> None:
    if not TELEGRAM_AUTO_SET_WEBHOOK:
        return

    try:
        await set_telegram_webhook()
        print("Telegram webhook configured")
    except Exception as exc:
        print(f"Telegram webhook setup failed: {exc}")


@app.post("/telegram/webhook", tags=["Telegram"])
async def telegram_webhook(
    update: dict[str, Any],
    db: Session = Depends(get_db),
    x_telegram_bot_api_secret_token: str | None = Header(default=None, alias="X-Telegram-Bot-Api-Secret-Token"),
):
    if TELEGRAM_WEBHOOK_SECRET and x_telegram_bot_api_secret_token != TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid Telegram secret token")

    callback = update.get("callback_query")
    if isinstance(callback, dict):
        await _handle_order_callback(callback, db)

    message = update.get("message")
    if isinstance(message, dict):
        await _handle_start_command(message, db)
        await _handle_any_message_ping(message, db)   # ✅ notify kitchen on ANY message

    return {"ok": True}


@app.post("/telegram/webhook/set", tags=["Telegram"], dependencies=[AdminOnly])
async def telegram_webhook_set() -> dict:
    return await set_telegram_webhook()


@app.get("/telegram/webhook/info", tags=["Telegram"], dependencies=[AdminOnly])
async def telegram_webhook_info() -> dict:
    return await tg_post("getWebhookInfo", {})


@app.post("/telegram/webhook/delete", tags=["Telegram"], dependencies=[AdminOnly])
async def telegram_webhook_delete() -> dict:
    return await tg_post("deleteWebhook", {"drop_pending_updates": False})


@app.get(
    "/telegram/users",
    response_model=list[TelegramUserOut],
    tags=["Telegram"],
    dependencies=[AdminOnly],
)
def get_all_telegram_users(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    users = (
        db.query(TelegramUserModel)
        .order_by(TelegramUserModel.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return users

async def _handle_any_message_ping(message: dict, db: Session) -> None:
    """
    When user types anything (after scanning QR /start), notify kitchen group
    with table_code + username/telegram_id.
    """
    text = (message.get("text") or "").strip()
    if not text:
        return

    from_user = message.get("from") or {}
    telegram_id = str(from_user.get("id") or "")
    if not telegram_id:
        return

    username = from_user.get("username")

    # get latest table code stored in DB
    user = db.query(TelegramUserModel).filter(TelegramUserModel.telegram_id == telegram_id).first()
    table_code = user.last_table_code if user else None

    # If message is "/start TB001", we can parse TB001 too (more reliable on first time)
    if text.startswith("/start"):
        parts = text.split(maxsplit=1)
        if len(parts) == 2 and parts[1].strip():
            table_code = parts[1].strip()

    try:
        await notify_kitchen_user_ping(
            table_code=table_code,
            username=username,          # your service can use @username if exists
            telegram_id=telegram_id,
            text=text
        )
    except Exception as exc:
        print("notify_kitchen_user_ping failed:", exc)
