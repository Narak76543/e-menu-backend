import os
import httpx
from typing import Any

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
KITCHEN_CHAT_ID = os.getenv("KITCHEN_CHAT_ID", "")
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def build_order_keyboard(order_id: str) -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Accept", "callback_data": f"order:accept:{order_id}"},
                {"text": "❌ Cancel", "callback_data": f"order:cancel:{order_id}"},
            ]
        ]
    }


async def tg_post(method: str, payload: dict) -> dict:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN missing in .env")

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(f"{TG_API}/{method}", json=payload)
        r.raise_for_status()
        return r.json()


async def send_message(chat_id: str, text: str, reply_markup: dict | None = None) -> dict:
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return await tg_post("sendMessage", payload)


async def answer_callback(callback_query_id: str, text: str = "OK") -> dict:
    return await tg_post("answerCallbackQuery", {
        "callback_query_id": callback_query_id,
        "text": text,
        "show_alert": False,
    })


async def edit_message(chat_id: str, message_id: int, text: str, reply_markup: dict | None = None) -> dict:
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "HTML"}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    return await tg_post("editMessageText", payload)


def format_order_message(order: Any, items: list[Any], table_code: str) -> str:
    lines = []
    lines.append("🍽 <b>New Order</b>")
    lines.append(f"Order ID: <code>{order.id}</code>")
    lines.append(f"Table: <b>{table_code}</b>")

    note = getattr(order, "note", None)
    if note:
        lines.append(f"Note: <i>{note}</i>")

    lines.append("")
    lines.append("<b>Items</b>")

    total = 0.0
    for it in items:
        qty = int(getattr(it, "qty", 1) or 1)
        subtotal = float(getattr(it, "subtotal", 0) or 0)
        price = float(getattr(it, "price", 0) or 0)
        total += subtotal
        lines.append(f"- <code>{it.product_id}</code> x{qty}  ({price:.2f}) = <b>{subtotal:.2f}</b>")

    lines.append("")
    lines.append(f"Total: <b>{float(getattr(order, 'total_amount', total) or total):.2f}</b>")
    return "\n".join(lines)


async def notify_kitchen_new_order(order: Any, items: list[Any], table_code: str) -> None:
    if not KITCHEN_CHAT_ID:
        print("KITCHEN_CHAT_ID missing; skip notify")
        return

    text = format_order_message(order, items, table_code)
    kb = build_order_keyboard(str(order.id))
    await send_message(KITCHEN_CHAT_ID, text, reply_markup=kb)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
KITCHEN_CHAT_ID = os.getenv("KITCHEN_CHAT_ID", "")
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

async def send_message(chat_id: str, text: str) -> dict:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN missing in .env")
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            f"{TG_API}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
        )
        r.raise_for_status()
        return r.json()


async def notify_kitchen_user_ping(table_code: str | None, username: str | None, telegram_id: str, text: str | None = None):
    if not KITCHEN_CHAT_ID:
        print("KITCHEN_CHAT_ID missing; skip notify")
        return

    who = f"@{username}" if username else f"<code>{telegram_id}</code>"
    msg = "👤 <b>Customer Message</b>\n"
    msg += f"Table: <b>{table_code or 'UNKNOWN'}</b>\n"
    msg += f"User: {who}\n"
    if text:
        msg += f"Text: <i>{text}</i>"

    await send_message(KITCHEN_CHAT_ID, msg)