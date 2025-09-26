from pathlib import Path

path = Path('post_flow.py')
text = path.read_text(encoding='utf-8')
old = '        await message.answer(\n            "Достигнут лимит в 6 фото. Нажмите «Готово» или удалите лишние, отправив «{cancel_label}».",\n            keyboard=photos_keyboard(uid),\n        )\n'
new = '        await message.answer(\n            f"Достигнут лимит в 6 фото. Нажмите «Готово» или удалите лишние, отправив «{cancel_label}».",\n            keyboard=photos_keyboard(uid),\n        )\n'
if old not in text:
    raise SystemExit('cancel message snippet not found')
text = text.replace(old, new, 1)
path.write_text(text, encoding='utf-8')
