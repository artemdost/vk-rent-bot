"""
Обработчики для проверки договоров аренды.
"""
import logging
from vkbottle import Keyboard, KeyboardButtonColor, Text
from vkbottle.bot import Message
from bot.bot_instance import bot
from bot.states import ContractStates, CONTRACT_PROMPTS
from bot.constants import Button, Message as Msg
from bot.services.document_parser import DocumentParser
from bot.services.contract_analyzer import ContractAnalyzer, RiskLevel


# Инициализация сервисов
document_parser = DocumentParser()
contract_analyzer = ContractAnalyzer()
logger = logging.getLogger(__name__)


@bot.on.message(text=Button.CHECK_CONTRACT)
async def start_contract_check(message: Message):
    """Начало проверки договора."""
    # Устанавливаем состояние ожидания документа
    await bot.state_dispenser.set(message.peer_id, ContractStates.UPLOAD)

    # Клавиатура с кнопкой отмены
    kb = Keyboard(inline=True)
    kb.add(Text(Button.CANCEL), color=KeyboardButtonColor.NEGATIVE)

    await message.answer(
        CONTRACT_PROMPTS[ContractStates.UPLOAD],
        keyboard=kb.get_json()
    )


@bot.on.message(state=ContractStates.UPLOAD)
async def handle_contract_upload(message: Message):
    """Обработка загруженного документа."""
    # Проверка на отмену
    if message.text and message.text.lower() in [Button.CANCEL.lower(), Button.MENU.lower(), "отмена", "меню"]:
        await bot.state_dispenser.delete(message.peer_id)

        # Возвращаем главное меню
        from bot.keyboards.menu import main_menu_inline
        await message.answer(
            "❌ Проверка договора отменена.\n\nВыберите действие:",
            keyboard=main_menu_inline()
        )
        return

    # Получаем вложения
    attachments = message.attachments

    if not attachments:
        # Если нет вложений, напоминаем пользователю
        kb = Keyboard(inline=True)
        kb.add(Text(Button.CANCEL), color=KeyboardButtonColor.NEGATIVE)

        await message.answer(
            Msg.CONTRACT_ERROR_NO_FILES + "\n\n" + CONTRACT_PROMPTS[ContractStates.UPLOAD],
            keyboard=kb.get_json()
        )
        return

    # Переходим в состояние обработки
    await bot.state_dispenser.set(message.peer_id, ContractStates.PROCESSING)

    # Отправляем сообщение о начале анализа
    await message.answer(CONTRACT_PROMPTS[ContractStates.PROCESSING])

    try:
        # Извлекаем текст из всех вложений
        all_texts = []
        processed_files = []

        for attachment in attachments:
            # Получаем описание типа файла
            file_type = document_parser.get_file_type_description(attachment)

            # Информируем пользователя о прогрессе
            await message.answer(Msg.CONTRACT_RECEIVED.format(file_type=file_type))

            # Извлекаем текст
            text = await document_parser.extract_text_from_attachment(attachment)

            if text:
                all_texts.append(text)
                processed_files.append(file_type)
            else:
                await message.answer(f"⚠️ Не удалось прочитать {file_type}")

        if not all_texts:
            # Если не удалось извлечь текст ни из одного файла
            await bot.state_dispenser.delete(message.peer_id)

            kb = Keyboard(inline=True)
            kb.add(Text(Button.CHECK_CONTRACT), color=KeyboardButtonColor.POSITIVE)
            kb.row()
            kb.add(Text(Button.MENU), color=KeyboardButtonColor.NEGATIVE)

            await message.answer(
                Msg.CONTRACT_ERROR_PARSE + "\n\n" +
                "Попробуйте отправить документ в другом формате или более четкие фотографии.",
                keyboard=kb.get_json()
            )
            return

        # Объединяем текст из всех файлов
        combined_text = "\n\n".join(all_texts)

        # Информируем о начале анализа
        files_info = f"📂 Обработано файлов: {len(processed_files)}"
        await message.answer(f"{files_info}\n\n{Msg.CONTRACT_ANALYZING}")

        # Анализируем договор
        analysis_result = await contract_analyzer.analyze_contract(combined_text)

        # Переходим в состояние результатов
        await bot.state_dispenser.set(message.peer_id, ContractStates.RESULTS)

        # Форматируем результат для VK
        formatted_result = contract_analyzer.format_analysis_for_vk(analysis_result)

        # Разбиваем на части если слишком длинный
        max_message_length = 4000
        if len(formatted_result) > max_message_length:
            # Отправляем по частям
            parts = []
            current_part = []
            current_length = 0

            for line in formatted_result.split('\n'):
                if current_length + len(line) + 1 > max_message_length:
                    parts.append('\n'.join(current_part))
                    current_part = [line]
                    current_length = len(line)
                else:
                    current_part.append(line)
                    current_length += len(line) + 1

            if current_part:
                parts.append('\n'.join(current_part))

            # Отправляем части
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    # Последняя часть с клавиатурой
                    kb = Keyboard(inline=True)
                    kb.add(Text(Button.CHECK_CONTRACT), color=KeyboardButtonColor.POSITIVE)
                    kb.row()
                    kb.add(Text(Button.MENU), color=KeyboardButtonColor.PRIMARY)

                    await message.answer(
                        part + "\n\n" + Msg.CONTRACT_BACK_TO_MENU,
                        keyboard=kb.get_json()
                    )
                else:
                    await message.answer(part)

        else:
            # Отправляем результат с клавиатурой
            kb = Keyboard(inline=True)
            kb.add(Text(Button.CHECK_CONTRACT), color=KeyboardButtonColor.POSITIVE)
            kb.row()
            kb.add(Text(Button.MENU), color=KeyboardButtonColor.PRIMARY)

            await message.answer(
                formatted_result + "\n\n" + Msg.CONTRACT_BACK_TO_MENU,
                keyboard=kb.get_json()
            )

        # Очищаем состояние
        await bot.state_dispenser.delete(message.peer_id)

    except Exception as e:
        logger.error(f"Ошибка при анализе договора: {e}", exc_info=True)

        # Очищаем состояние
        await bot.state_dispenser.delete(message.peer_id)

        # Отправляем сообщение об ошибке
        kb = Keyboard(inline=True)
        kb.add(Text(Button.CHECK_CONTRACT), color=KeyboardButtonColor.POSITIVE)
        kb.row()
        kb.add(Text(Button.MENU), color=KeyboardButtonColor.NEGATIVE)

        await message.answer(
            Msg.CONTRACT_ERROR_ANALYSIS + "\n\n" +
            "Возможные причины:\n" +
            "• Файл поврежден или имеет неподдерживаемый формат\n" +
            "• Временные проблемы с сервисом анализа\n" +
            "• Слишком большой объем текста\n\n" +
            "Попробуйте еще раз или обратитесь в поддержку.",
            keyboard=kb.get_json()
        )


@bot.on.message(state=ContractStates.RESULTS)
async def handle_results_state(message: Message):
    """Обработка состояния результатов."""
    # Любое сообщение в этом состоянии возвращает в меню
    await bot.state_dispenser.delete(message.peer_id)

    from bot.keyboards.menu import main_menu_inline

    if message.text == Button.CHECK_CONTRACT:
        # Начинаем новую проверку
        await start_contract_check(message)
    else:
        # Возвращаем в меню
        await message.answer(
            "Выберите действие:",
            keyboard=main_menu_inline()
        )