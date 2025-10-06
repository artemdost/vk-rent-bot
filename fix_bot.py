# fix_bot.py
import re
import os

def fix_state_dispenser_delete(file_path):
    """
    Исправляет все вызовы bot.state_dispenser.delete(), 
    оборачивая их в try-except блоки.
    """
    
    # Читаем файл
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Создаем резервную копию
    backup_path = file_path + '.backup'
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Создана резервная копия: {backup_path}")
    
    # Паттерн для поиска await bot.state_dispenser.delete(...)
    pattern = r'(\s*)(await bot\.state_dispenser\.delete\([^)]+\))'
    
    def replace_func(match):
        indent = match.group(1)
        delete_call = match.group(2)
        
        # Проверяем, не обернут ли уже в try-except
        # Ищем контекст вокруг совпадения
        start = max(0, match.start() - 100)
        context = content[start:match.end()]
        
        if 'try:' in context and 'except' in context:
            # Уже обернут, не трогаем
            return match.group(0)
        
        # Оборачиваем в try-except
        replacement = f"{indent}try:\n{indent}    {delete_call}\n{indent}except (KeyError, Exception):\n{indent}    pass"
        return replacement
    
    # Заменяем все вхождения
    fixed_content = re.sub(pattern, replace_func, content)
    
    # Подсчитываем количество замен
    original_count = len(re.findall(pattern, content))
    
    # Сохраняем исправленный файл
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    print(f"✅ Исправлено {original_count} вызовов bot.state_dispenser.delete() в {file_path}")
    return original_count


if __name__ == "__main__":
    # Путь к вашему файлу
    file_to_fix = "post_flow.py"
    
    if not os.path.exists(file_to_fix):
        print(f"❌ Файл {file_to_fix} не найден!")
        exit(1)
    
    print(f"🔧 Начинаю исправление {file_to_fix}...")
    count = fix_state_dispenser_delete(file_to_fix)
    
    if count > 0:
        print(f"✅ Готово! Исправлено {count} мест.")
        print(f"📝 Резервная копия сохранена как {file_to_fix}.backup")
        print(f"⚠️  Проверьте файл перед запуском бота!")
    else:
        print("ℹ️  Ничего не требует исправления или уже исправлено.")