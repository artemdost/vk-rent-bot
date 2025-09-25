# test.py
import os, time, requests, json
from dotenv import load_dotenv

load_dotenv()  # читает .env

GROUP_ID = int(os.getenv("GROUP_ID", "0"))
GROUP_TOKEN = os.getenv("GROUP_TOKEN")
API_V = os.getenv("VK_API_VERSION", "5.131")

def send_test_scheduled():
    owner_id = -abs(GROUP_ID)
    publish_date = int(time.time()) + 600  # через 10 минут
    params = {
        "access_token": GROUP_TOKEN,
        "owner_id": owner_id,
        "from_group": 1,
        "message": "Тест: отправка в отложенные (бот). Удалить/игнорировать.",
        "publish_date": publish_date,
        "v": API_V
    }
    r = requests.post("https://api.vk.com/method/wall.post", data=params, timeout=15)
    try:
        resp = r.json()
    except Exception:
        print("Не JSON ответ:", r.text)
        return
    print(json.dumps(resp, ensure_ascii=False, indent=2))
    return resp

if __name__ == "__main__":
    print("GROUP_ID =", GROUP_ID)
    print("Have GROUP_TOKEN? ", bool(GROUP_TOKEN))
    send_test_scheduled()
