"""
SMS (Eskiz / SMS Gateway) va Telegram Bot orqali ogohlantirishlar
"""
import httpx
import logging

logger = logging.getLogger("notifications_service")


async def send_sms(phone: str, message: str, api_key: str = None) -> dict:
    """
    Qarzdor mijozga SMS yuborish
    Eskiz.uz yoki umumiy SMS API integratsiyasi
    """
    clean_phone = "".join(filter(str.isdigit, phone))
    logger.info(f"[SMS] Yuborilmoqda -> Tel: {clean_phone}, Xabar: {message}")

    if not api_key:
        # Dev / test muhitida simulyatsiya
        logger.info(f"[SMS SIMULATION] API kalit yo'q, test rejimida yuborildi.")
        return {"success": True, "simulated": True, "phone": clean_phone, "message": message}

    try:
        # Eskiz.uz yoki SMS provayderiga HTTP POST
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {"Authorization": f"Bearer {api_key}"}
            payload = {
                "mobile_phone": clean_phone,
                "message": message,
                "from": "4546",
            }
            # Standart Eskiz send endpoint
            resp = await client.post("https://notify.eskiz.uz/api/message/sms/send", headers=headers, data=payload)
            if resp.status_code in [200, 201]:
                return {"success": True, "data": resp.json()}
            else:
                logger.warning(f"[SMS ERROR] Provayder xatosi: {resp.status_code} - {resp.text}")
                return {"success": False, "error": resp.text}
    except Exception as e:
        logger.error(f"[SMS EXCEPTION] Xatolik: {e}")
        return {"success": False, "error": str(e)}


async def send_telegram_alert(token: str, chat_id: str, text: str) -> bool:
    """
    Telegram guruhiga yoki kanaliga real-time ogohlantirish xabari yuborish
    (Ofitsiant chaqiruvlari, yangi buyurtmalar, kassa xabarlari)
    """
    if not token or not chat_id:
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(url, json=payload)
            return resp.status_code == 200
    except Exception as e:
        logger.warning(f"[TELEGRAM ERROR] Telegram xabar yuborilmadi: {e}")
        return False


# Aliases
send_telegram_notification = send_telegram_alert
send_debt_sms_reminder = send_sms

