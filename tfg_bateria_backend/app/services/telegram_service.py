import requests


def send_telegram_message(chat_id: str, text: str, bot_token: str) -> None:
    """Send *text* to Telegram *chat_id* using the given *bot_token*."""
    if not bot_token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as exc:  # pragma: no cover - log only
        print(f"[TELEGRAM] Error sending message: {exc}")
