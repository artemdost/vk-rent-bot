# post_submit.py
import os
import time
import logging
import requests
from typing import Optional, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_V = os.getenv("VK_API_VERSION", "5.131")
GROUP_ID = int(os.getenv("GROUP_ID", "0"))
GROUP_TOKEN = os.getenv("GROUP_TOKEN")

def _vk_wall_post(params: Dict[str, Any]) -> Dict[str, Any]:
    try:
        r = requests.post("https://api.vk.com/method/wall.post", data=params, timeout=15)
        try:
            return r.json()
        except Exception:
            logger.exception("Invalid JSON from VK (raw): %s", r.text)
            return {"error": {"error_msg": "Invalid JSON response", "raw": r.text}}
    except Exception as e:
        logger.exception("HTTP error to VK: %s", e)
        return {"error": {"error_msg": str(e)}}

def send_to_scheduled(text: str, attachments: Optional[str] = None, delay_seconds: int = 3600) -> Dict[str, Any]:
    """
    Send post as community to scheduled (publish_date = now + delay_seconds).
    Returns VK JSON response.
    """
    if not GROUP_TOKEN:
        return {"error": {"error_msg": "GROUP_TOKEN not configured"}}
    if GROUP_ID == 0:
        return {"error": {"error_msg": "GROUP_ID not configured"}}

    owner_id = -abs(int(GROUP_ID))
    publish_date = int(time.time()) + int(delay_seconds)
    if not isinstance(text, str):
        text = str(text)
    text_len = len(text)
    params = {
        "access_token": GROUP_TOKEN,
        "owner_id": owner_id,
        "from_group": 1,
        "message": text,
        "publish_date": publish_date,
        "v": API_V,
    }
    logger.info("VK: send scheduled owner=%s publish_date=%s text_len=%s", owner_id, publish_date, text_len)
    resp = _vk_wall_post(params)


    if not isinstance(text, str):
        text = str(text)

    resp = _vk_wall_post(params)
    logger.info("VK response: %s", resp)
    return resp

def build_text_from_draft(draft: dict) -> str:
    parts = []
    if draft.get("district"): parts.append(f"🏙 Район: {draft.get('district')}")
    if draft.get("address"): parts.append(f"📍 Адрес: {draft.get('address')}")
    if draft.get("floor") is not None: parts.append(f"🏢 Этаж: {draft.get('floor')}")
    if draft.get("rooms") is not None: parts.append(f"🚪 Комнат: {draft.get('rooms')}")
    if draft.get("price") is not None: parts.append(f"💰 Цена: {draft.get('price')}")
    if draft.get("description"):
        parts.append("")
        parts.append(draft.get("description"))
    return "\n".join(parts).strip()
