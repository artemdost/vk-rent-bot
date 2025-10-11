"""
Сервис для извлечения текста из различных типов документов.
Поддерживает PDF, DOCX, TXT и изображения.
"""
import os
import tempfile
import requests
from typing import Optional, List, Dict, Any
import logging
import base64
import io

# Импорты для работы с документами
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logging.warning("PyPDF2 не установлен. PDF файлы не будут обрабатываться.")

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    logging.warning("python-docx не установлен. DOCX файлы не будут обрабатываться.")

try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logging.warning("PIL или pytesseract не установлены. OCR для изображений недоступен.")


class DocumentParser:
    """Парсер документов различных форматов."""

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    SUPPORTED_IMAGE_FORMATS = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
    SUPPORTED_DOCUMENT_FORMATS = ['.pdf', '.docx', '.txt']

    def __init__(self):
        """Инициализация парсера документов."""
        self.logger = logging.getLogger(__name__)

    async def download_file(self, url: str) -> Optional[bytes]:
        """
        Скачивает файл по URL.

        Args:
            url: URL файла

        Returns:
            Содержимое файла в байтах или None при ошибке
        """
        try:
            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()

            # Проверка размера файла
            content_length = response.headers.get('Content-Length')
            if content_length and int(content_length) > self.MAX_FILE_SIZE:
                self.logger.error(f"Файл слишком большой: {content_length} байт")
                return None

            # Загрузка с ограничением размера
            content = b""
            for chunk in response.iter_content(chunk_size=8192):
                content += chunk
                if len(content) > self.MAX_FILE_SIZE:
                    self.logger.error("Файл превышает максимальный размер")
                    return None

            return content

        except requests.RequestException as e:
            self.logger.error(f"Ошибка загрузки файла: {e}")
            return None

    def extract_text_from_pdf(self, content: bytes) -> Optional[str]:
        """
        Извлекает текст из PDF файла.

        Args:
            content: Содержимое PDF файла

        Returns:
            Извлеченный текст или None при ошибке
        """
        if not PDF_AVAILABLE:
            return None

        try:
            pdf_file = io.BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            text = ""
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n"

            return text.strip()

        except Exception as e:
            self.logger.error(f"Ошибка извлечения текста из PDF: {e}")
            return None

    def extract_text_from_docx(self, content: bytes) -> Optional[str]:
        """
        Извлекает текст из DOCX файла.

        Args:
            content: Содержимое DOCX файла

        Returns:
            Извлеченный текст или None при ошибке
        """
        if not DOCX_AVAILABLE:
            return None

        try:
            docx_file = io.BytesIO(content)
            doc = Document(docx_file)

            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"

            # Также извлекаем текст из таблиц
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        text += cell.text + " "
                    text += "\n"

            return text.strip()

        except Exception as e:
            self.logger.error(f"Ошибка извлечения текста из DOCX: {e}")
            return None

    def extract_text_from_image(self, content: bytes) -> Optional[str]:
        """
        Извлекает текст из изображения с помощью OCR.

        Args:
            content: Содержимое изображения

        Returns:
            Извлеченный текст или None при ошибке
        """
        if not OCR_AVAILABLE:
            # Если OCR недоступен, возвращаем заглушку
            return "[Изображение документа - требуется ручная проверка]"

        try:
            image = Image.open(io.BytesIO(content))

            # Конвертация в RGB если необходимо
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # OCR с русским языком
            text = pytesseract.image_to_string(image, lang='rus+eng')

            return text.strip()

        except Exception as e:
            self.logger.error(f"Ошибка OCR: {e}")
            return "[Не удалось распознать текст в изображении]"

    def extract_text_from_txt(self, content: bytes) -> Optional[str]:
        """
        Извлекает текст из TXT файла.

        Args:
            content: Содержимое TXT файла

        Returns:
            Извлеченный текст или None при ошибке
        """
        try:
            # Пробуем разные кодировки
            for encoding in ['utf-8', 'windows-1251', 'cp866']:
                try:
                    return content.decode(encoding)
                except UnicodeDecodeError:
                    continue

            # Если не удалось декодировать, пробуем с игнорированием ошибок
            return content.decode('utf-8', errors='ignore')

        except Exception as e:
            self.logger.error(f"Ошибка чтения TXT файла: {e}")
            return None

    async def extract_text_from_attachment(self, attachment: Dict[str, Any]) -> Optional[str]:
        """
        Извлекает текст из вложения VK.

        Args:
            attachment: Объект вложения из VK API

        Returns:
            Извлеченный текст или None при ошибке
        """
        try:
            attachment_type = attachment.get('type')

            # Обработка документов
            if attachment_type == 'doc':
                doc = attachment.get('doc', {})
                url = doc.get('url')
                ext = doc.get('ext', '').lower()

                if not url:
                    return None

                # Скачиваем файл
                content = await self.download_file(url)
                if not content:
                    return None

                # Извлекаем текст в зависимости от типа
                if ext == 'pdf' or url.lower().endswith('.pdf'):
                    return self.extract_text_from_pdf(content)
                elif ext == 'docx' or url.lower().endswith('.docx'):
                    return self.extract_text_from_docx(content)
                elif ext == 'txt' or url.lower().endswith('.txt'):
                    return self.extract_text_from_txt(content)
                else:
                    self.logger.warning(f"Неподдерживаемый тип документа: {ext}")
                    return None

            # Обработка изображений
            elif attachment_type == 'photo':
                photo = attachment.get('photo', {})

                # Ищем изображение максимального размера
                max_size_url = None
                max_size = 0

                for size_key in ['photo_2560', 'photo_1280', 'photo_807', 'photo_604', 'photo_130', 'photo_75']:
                    if size_key in photo:
                        max_size_url = photo[size_key]
                        break

                # Альтернативный способ получения URL через sizes
                if not max_size_url and 'sizes' in photo:
                    sizes = sorted(photo['sizes'], key=lambda x: x.get('width', 0) * x.get('height', 0), reverse=True)
                    if sizes:
                        max_size_url = sizes[0].get('url')

                if not max_size_url:
                    return None

                # Скачиваем изображение
                content = await self.download_file(max_size_url)
                if not content:
                    return None

                # Извлекаем текст с помощью OCR
                return self.extract_text_from_image(content)

            else:
                self.logger.warning(f"Неподдерживаемый тип вложения: {attachment_type}")
                return None

        except Exception as e:
            self.logger.error(f"Ошибка обработки вложения: {e}")
            return None

    async def extract_all_texts(self, attachments: List[Dict[str, Any]]) -> List[str]:
        """
        Извлекает текст из всех вложений.

        Args:
            attachments: Список вложений из VK API

        Returns:
            Список извлеченных текстов
        """
        texts = []

        for attachment in attachments:
            text = await self.extract_text_from_attachment(attachment)
            if text:
                texts.append(text)

        return texts

    def get_file_type_description(self, attachment: Dict[str, Any]) -> str:
        """
        Получает описание типа файла для пользователя.

        Args:
            attachment: Объект вложения из VK API

        Returns:
            Описание типа файла
        """
        attachment_type = attachment.get('type')

        if attachment_type == 'doc':
            doc = attachment.get('doc', {})
            ext = doc.get('ext', '').upper()
            title = doc.get('title', 'документ')
            return f"{ext} документ '{title}'"
        elif attachment_type == 'photo':
            return "изображение"
        else:
            return "файл"