# Быстрый старт 🚀

Инструкция для быстрого запуска бота (5 минут).

## 1️⃣ Установка

```bash
# Клонировать/скачать проект
cd vk-rent-bot

# Создать виртуальное окружение
python -m venv venv

# Активировать venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt
```

## 2️⃣ Настройка

### Создать `.env` файл:

```bash
cp .env.example .env
```

### Заполнить `.env`:

```env
# Минимально необходимые настройки:
USER_TOKEN=ваш_user_token_или_group_token
GROUP_ID=123456789

# Остальные - опционально
VK_API_VERSION=5.199
SUPPORT_URL=https://vk.com/your_support
MAX_SEARCHES_UNSUBSCRIBED=3
```

### Где взять токены?

**USER_TOKEN (рекомендуется):**
1. [vk.com/apps?act=manage](https://vk.com/apps?act=manage) → Создать приложение
2. Получить токен с правами: `photos`, `wall`, `groups`, `messages`, `offline`

**GROUP_TOKEN (альтернатива):**
1. Настройки сообщества → Работа с API → Создать ключ
2. Права: `messages`, `photos`, `wall`

## 3️⃣ Настройка сообщества VK

1. Добавьте бота в сообщество (через токен)
2. Настройки → Сообщения:
   - ✅ Включить сообщения сообщества
   - ✅ Разрешить добавление в беседы
3. Настройки → Работа с API:
   - ✅ Long Poll API → Включено
   - ✅ Типы событий → Входящие сообщения

## 4️⃣ Проверка импортов (опционально)

Перед запуском рекомендуется проверить, что все модули импортируются корректно:

```bash
python test_imports.py
```

Должно вывести:
```
✅ All imports successful!
📊 Bot type: <class 'vkbottle.bot.bot.Bot'>
   Has run_forever: True
```

Если есть ошибки - смотрите [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

## 5️⃣ Запуск

```bash
python main.py
```

### Ожидаемый вывод:

```
2024-10-10 10:00:00 INFO bot: Starting bot: using USER_TOKEN
2024-10-10 10:00:00 INFO bot: Applied groups.getById patch with GROUP_ID=123456789
2024-10-10 10:00:00 INFO bot: Token check (groups.getById): {"response":[...]}
2024-10-10 10:00:00 INFO bot: Bot starting...
```

## 6️⃣ Проверка работы

1. Напишите боту в ЛС: `/start`
2. Должно появиться главное меню с кнопками:
   - **Выложить** - создать объявление
   - **Посмотреть** - поиск объявлений
   - **Поддержка** - контакты

## ⚠️ Возможные проблемы

### Ошибка: "RuntimeError: Нужен USER_TOKEN или GROUP_TOKEN"
→ Проверьте `.env` файл, добавьте токен

### Ошибка: "groups.getById is undefined"
→ Убедитесь, что `GROUP_ID` указан в `.env`

### Бот не отвечает
→ Проверьте:
- Long Poll включен в настройках сообщества
- Бот добавлен в сообщество
- Токен валиден (не истёк)

### Ошибка загрузки фото
→ Добавьте `UPLOAD_TOKEN` с правами `photos,wall,groups`

## 📚 Дальше

- **README.md** - полная документация
- **TROUBLESHOOTING.md** - решение проблем
- **AI_GUIDE.md** - для AI-ассистентов
- **MIGRATION.md** - если переходите со старой версии

## 🆘 Помощь

Если что-то не работает:
1. Запустите `python test_imports.py` для диагностики
2. Смотрите **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - там решения всех типичных проблем
3. Проверьте логи в консоли
4. Убедитесь, что все зависимости установлены
5. Проверьте настройки сообщества VK
6. Создайте Issue в репозитории

---

**Готово! Бот работает! 🎉**
