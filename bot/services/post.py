"""
Сервис для публикации постов в VK.
Загрузка фото и отправка постов в отложенные записи.
"""
import time
import logging
import requests
from typing import Optional, Dict, Any, List

from bot.config import (
    GROUP_ID,
    GROUP_TOKEN,
    UPLOAD_TOKEN,
    API_V,
    REQUEST_TIMEOUT,
    DEFAULT_SCHEDULE_DELAY,
)
from bot.services.vk_api import vk_api_call

logger = logging.getLogger("post_service")


def upload_photos_to_group(photo_urls: List[str]) -> Dict[str, Any]:
    """
    Загружает список URL'ов фото в сообщество.

    Args:
        photo_urls: Список URL фотографий

    Returns:
        {"response": {"attachments": "photo<owner>_<id>,..."}}
        или {"error": {...}}
    """
    if not photo_urls:
        return {"response": {"attachments": None}}

    if GROUP_ID == 0:
        return {"error": {"error_msg": "GROUP_ID not configured"}}

    token_for_upload = UPLOAD_TOKEN or GROUP_TOKEN
    if not token_for_upload:
        return {
            "error": {
                "error_msg": "No UPLOAD_TOKEN or GROUP_TOKEN configured for photo upload"
            }
        }

    attachments: List[str] = []
    max_photos = 6

    for idx, url in enumerate(photo_urls[:max_photos], start=1):
        logger.info("Downloading photo #%s from: %s", idx, url)

        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            img_bytes = resp.content
        except Exception as e:
            logger.exception("Failed to download %s: %s", url, e)
            return {"error": {"error_msg": f"Failed to download photo: {e}"}}

        # 1) Получаем upload_url
        get_upload = vk_api_call(
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

        # 2) Загружаем файл
        logger.info("Uploading to %s", upload_url)
        try:
            files = {"photo": ("photo.jpg", img_bytes)}
            up = requests.post(upload_url, files=files, timeout=REQUEST_TIMEOUT * 2)
            up.raise_for_status()
            upj = up.json()
        except Exception as e:
            logger.exception("Upload failed: %s", e)
            return {
                "error": {
                    "error_msg": f"Upload failed: {e}",
                    "raw": getattr(up, "text", None),
                }
            }

        server = upj.get("server")
        photo = upj.get("photo")
        hash_ = upj.get("hash")

        if not (server and photo and hash_):
            logger.error("Invalid upload response: %s", upj)
            return {"error": {"error_msg": "Invalid upload response", "raw": upj}}

        # 3) Сохраняем фото
        save_resp = vk_api_call(
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
            return {
                "error": {
                    "error_msg": "saveWallPhoto returned unexpected response",
                    "raw": save_resp,
                }
            }

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


def send_to_scheduled(
    text: str,
    attachments: Optional[str] = None,
    delay_seconds: int = DEFAULT_SCHEDULE_DELAY,
) -> Dict[str, Any]:
    """
    Создаёт отложенный пост (wall.post с publish_date).

    Args:
        text: Текст поста
        attachments: Строка вложений (например, "photo123_456,photo123_789")
        delay_seconds: Задержка публикации в секундах

    Returns:
        Ответ VK API
    """
    if GROUP_ID == 0:
        return {"error": {"error_msg": "GROUP_ID not configured"}}

    token_for_post = UPLOAD_TOKEN or GROUP_TOKEN
    if not token_for_post:
        return {
            "error": {
                "error_msg": "No token configured for posting (UPLOAD_TOKEN or GROUP_TOKEN)"
            }
        }

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

    logger.info(
        "Posting scheduled: owner=%s publish_date=%s text_len=%s attachments=%s",
        owner_id,
        publish_date,
        len(text) if isinstance(text, str) else 0,
        bool(attachments),
    )

    resp = vk_api_call("wall.post", params, token=token_for_post)
    logger.info("wall.post response: %s", resp)
    return resp
