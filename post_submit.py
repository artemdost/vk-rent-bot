# post_submit.py
"""
Загрузка фото и отправка поста в отложенные записи сообщества VK.

Требования (в .env):
  GROUP_ID         - id сообщества (число)
  GROUP_TOKEN      - (опционально) токен сообщества (если нужен для wall.post)
  UPLOAD_TOKEN     - (рекомендовано) user-token администратора с правами photos,wall,groups,offline
  VK_API_VERSION   - версия VK API (по умолчанию 5.131)
"""

import os
import time
import logging
from typing import Optional, Dict, Any, List
import requests

logger = logging.getLogger("post_submit")
logger.setLevel(logging.INFO)

API_V = os.getenv("VK_API_VERSION", "5.131")
try:
    GROUP_ID = int(os.getenv("GROUP_ID", "0"))
except Exception:
    GROUP_ID = 0

GROUP_TOKEN = os.getenv("GROUP_TOKEN")      # можно использовать для wall.post
UPLOAD_TOKEN = os.getenv("UPLOAD_TOKEN")    # рекомендуется: user-token админа для загрузки фото/постинга

REQUEST_TIMEOUT = 30


def _vk_call(method: str, params: Dict[str, Any], token: Optional[str] = None) -> Dict[str, Any]:
    """
    Универсальный вызов VK API (POST).
    Если token передан, будет использован как access_token; иначе ожидается, что в params он уже есть.
    Возвращает распарсенный JSON.
    """
    url = f"https://api.vk.com/method/{method}"
    params = dict(params)  # копируем, чтобы не ломать внешний dict
    if token:
        params["access_token"] = token
    try:
        r = requests.post(url, data=params, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
    except Exception as e:
        logger.exception("HTTP error calling %s: %s", method, e)
        return {"error": {"error_msg": str(e)}}
    try:
        j = r.json()
    except Exception as e:
        logger.exception("Invalid JSON from VK %s: %s -- raw: %s", method, e, r.text[:300])
        return {"error": {"error_msg": "Invalid JSON response", "raw": r.text}}
    return j


def upload_photos_to_group(photo_urls: List[str]) -> Dict[str, Any]:
    """
    Загружает список URL'ов фото в сообщество и возвращает {"response": {"attachments": "photo<owner>_<id>,..."}}
    Требует рабочий токен (UPLOAD_TOKEN предпочтительный).
    """
    if not photo_urls:
        return {"response": {"attachments": None}}

    if GROUP_ID == 0:
        return {"error": {"error_msg": "GROUP_ID not configured"}}

    # какой токен использовать для upload/save/post:
    token_for_upload = UPLOAD_TOKEN or GROUP_TOKEN
    if not token_for_upload:
        return {"error": {"error_msg": "No UPLOAD_TOKEN or GROUP_TOKEN configured for photo upload"}}

    attachments: List[str] = []

    for idx, url in enumerate(photo_urls, start=1):
        logger.info("Downloading photo #%s from: %s", idx, url)
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            img_bytes = resp.content
        except Exception as e:
            logger.exception("Failed to download %s: %s", url, e)
            return {"error": {"error_msg": f"Failed to download photo: {e}"}}

        # 1) Получаем upload_url (user-token admin лучше)
        get_upload = _vk_call(
            "photos.getWallUploadServer",
            {"group_id": GROUP_ID, "v": API_V},
            token=token_for_upload,
        )
        if "error" in get_upload:
            logger.error("photos.getWallUploadServer error: %s", get_upload)
            return {"error": get_upload["error"]}
        upload_url = get_upload.get("response", {}).get("upload_url")
        if not upload_url:
            logger.error("No upload_url in response: %s", get_upload)
            return {"error": {"error_msg": "No upload_url returned"}}

        # 2) Загружаем файл на upload_url
        logger.info("Uploading to %s", upload_url)
        try:
            files = {"photo": ("photo.jpg", img_bytes)}
            up = requests.post(upload_url, files=files, timeout=REQUEST_TIMEOUT * 2)
            up.raise_for_status()
            upj = up.json()
        except Exception as e:
            logger.exception("Upload failed: %s", e)
            return {"error": {"error_msg": f"Upload failed: {e}", "raw": getattr(up, "text", None)}}

        server = upj.get("server")
        photo = upj.get("photo")
        hash_ = upj.get("hash")
        if not (server and photo and hash_):
            logger.error("Invalid upload response: %s", upj)
            return {"error": {"error_msg": "Invalid upload response", "raw": upj}}

        # 3) Сохраняем фото в группе
        save_resp = _vk_call(
            "photos.saveWallPhoto",
            {
                "group_id": GROUP_ID,
                "photo": photo,
                "server": server,
                "hash": hash_,
                "v": API_V,
            },
            token=token_for_upload,
        )
        if "error" in save_resp:
            logger.error("photos.saveWallPhoto error: %s", save_resp)
            return {"error": save_resp["error"]}

        saved = save_resp.get("response")
        if not saved or not isinstance(saved, list):
            logger.error("photos.saveWallPhoto unexpected: %s", save_resp)
            return {"error": {"error_msg": "saveWallPhoto returned unexpected response", "raw": save_resp}}

        item = saved[0]
        owner_id = item.get("owner_id")
        photo_id = item.get("id")
        if owner_id is None or photo_id is None:
            logger.error("saveWallPhoto missing owner_id/id: %s", item)
            return {"error": {"error_msg": "Invalid saved photo response", "raw": item}}

        attachments.append(f"photo{owner_id}_{photo_id}")
        logger.info("Saved photo: photo%s_%s", owner_id, photo_id)

    attachments_str = ",".join(attachments) if attachments else None
    logger.info("All photos uploaded; attachments=%s", attachments_str)
    return {"response": {"attachments": attachments_str}}


def send_to_scheduled(text: str, attachments: Optional[str] = None, delay_seconds: int = 3600) -> Dict[str, Any]:
    """
    Создаёт отложенный пост (wall.post с publish_date) от имени сообщества.
    Для корректной работы с from_group=1 рекомендуется использовать UPLOAD_TOKEN (user-token админа)
    или GROUP_TOKEN, если он даёт такие права в вашем кейсе.
    """
    if GROUP_ID == 0:
        return {"error": {"error_msg": "GROUP_ID not configured"}}

    # prefer UPLOAD_TOKEN for posting (it is user-token admin), fallback to GROUP_TOKEN
    token_for_post = UPLOAD_TOKEN or GROUP_TOKEN
    if not token_for_post:
        return {"error": {"error_msg": "No token configured for posting (UPLOAD_TOKEN or GROUP_TOKEN)"}}

    owner_id = -abs(int(GROUP_ID))
    publish_date = int(time.time()) + int(delay_seconds)
    params = {
        "owner_id": owner_id,
        "from_group": 1,
        "message": text,
        "publish_date": publish_date,
        "v": API_V,
    }
    if attachments:
        params["attachments"] = attachments

    logger.info("Posting scheduled: owner=%s publish_date=%s text_len=%s attachments=%s",
                owner_id, publish_date, len(text) if isinstance(text, str) else 0, bool(attachments))

    resp = _vk_call("wall.post", params, token=token_for_post)
    logger.info("wall.post response: %s", resp)
    return resp


def build_text_from_draft(draft: Dict[str, Any]) -> str:
    parts: List[str] = []
    if draft.get("district"):
        parts.append(f"🏙 Район: {draft.get('district')}")
    if draft.get("address"):
        parts.append(f"📍 Адрес: {draft.get('address')}")
    if draft.get("floor") is not None:
        parts.append(f"🏢 Этаж: {draft.get('floor')}")
    if draft.get("rooms") is not None:
        parts.append(f"🚪 Комнат: {draft.get('rooms')}")
    if draft.get("price") is not None:
        parts.append(f"💰 Цена: {draft.get('price')}")
    if draft.get("description"):
        parts.append("")
        parts.append(draft.get("description"))
    parts.append("")
    if draft.get("fio"):
        parts.append(f"👤 Контакт: {draft.get('fio')}")
    if draft.get("phone"):
        parts.append(f"📞 Телефон: {draft.get('phone')}")
    return "\n".join(parts).strip()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("GROUP_ID:", GROUP_ID, "Have GROUP_TOKEN?", bool(GROUP_TOKEN), "Have UPLOAD_TOKEN?", bool(UPLOAD_TOKEN))
