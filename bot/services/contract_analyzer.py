"""
Сервис для анализа договоров аренды с использованием Deepseek AI.
"""
import os
import json
import logging
import requests
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class RiskLevel(Enum):
    """Уровни риска."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ContractIssue:
    """Проблема в договоре."""
    title: str
    description: str
    risk_level: RiskLevel
    section: Optional[str] = None
    recommendation: Optional[str] = None


@dataclass
class ContractAnalysisResult:
    """Результат анализа договора."""
    overall_risk: RiskLevel
    summary: str
    issues: List[ContractIssue]
    positive_points: List[str]
    recommendations: List[str]
    key_terms: Dict[str, str]  # Ключевые условия (срок, цена, залог и т.д.)


class ContractAnalyzer:
    """Анализатор договоров аренды с использованием Deepseek API."""

    DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

    def __init__(self):
        """Инициализация анализатора."""
        self.logger = logging.getLogger(__name__)

        # Получаем API ключ Deepseek из переменных окружения
        self.api_key = os.getenv('DEEPSEEK_API_KEY')
        if not self.api_key:
            self.logger.warning("DEEPSEEK_API_KEY не установлен. Будет использоваться анализ на основе правил.")

    async def analyze_contract(self, text: str) -> ContractAnalysisResult:
        """
        Анализирует текст договора.

        Args:
            text: Текст договора

        Returns:
            Результат анализа
        """
        # Если есть API ключ, используем Deepseek
        if self.api_key:
            return await self._analyze_with_deepseek(text)
        else:
            # Используем встроенный анализ на основе правил
            return await self._analyze_with_rules(text)

    async def _analyze_with_deepseek(self, text: str) -> ContractAnalysisResult:
        """Анализ с использованием Deepseek API."""
        try:
            # Проверяем, есть ли изображения в тексте
            if "[IMAGE:" in text:
                # Если есть изображения, используем мультимодальную модель Deepseek
                messages = self._prepare_multimodal_messages(text)
                model = "deepseek-vision"  # Модель для обработки изображений
            else:
                # Для текста используем обычную модель
                prompt = self._create_analysis_prompt(text)
                messages = [
                    {
                        "role": "system",
                        "content": "Ты опытный юридический эксперт по договорам аренды жилья в России. Твоя задача - анализировать договоры и находить потенциальные риски для арендатора."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
                model = "deepseek-chat"

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 4000,
                "stream": False
            }

            response = requests.post(
                self.DEEPSEEK_API_URL,
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                return self._parse_ai_response(content)
            else:
                self.logger.error(f"Ошибка Deepseek API: {response.status_code} - {response.text}")
                return await self._analyze_with_rules(text)

        except requests.exceptions.Timeout:
            self.logger.error("Таймаут при обращении к Deepseek API")
            return await self._analyze_with_rules(text)
        except Exception as e:
            self.logger.error(f"Ошибка Deepseek API: {e}")
            return await self._analyze_with_rules(text)

    def _prepare_multimodal_messages(self, text: str) -> List[Dict]:
        """
        Подготавливает сообщения для мультимодальной модели Deepseek.

        Args:
            text: Текст с маркерами изображений [IMAGE:base64]

        Returns:
            Список сообщений для API
        """
        import re

        # Извлекаем все изображения из текста
        image_pattern = r'\[IMAGE:(.*?)\]'
        images = re.findall(image_pattern, text)

        # Убираем маркеры изображений из текста
        clean_text = re.sub(image_pattern, '[Изображение договора]', text)

        # Формируем сообщения с изображениями
        content = [
            {
                "type": "text",
                "text": f"""Проанализируй договор аренды на фотографиях и найди потенциальные проблемы.

{self._get_analysis_instructions()}

Если на изображениях есть текст, прочитай его и проанализируй.
Верни результат в формате JSON как указано выше."""
            }
        ]

        # Добавляем изображения
        for i, base64_image in enumerate(images[:5]):  # Ограничиваем до 5 изображений
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                }
            })

        return [
            {
                "role": "system",
                "content": "Ты опытный юридический эксперт по договорам аренды жилья в России. Твоя задача - анализировать договоры и находить потенциальные риски для арендатора."
            },
            {
                "role": "user",
                "content": content
            }
        ]

    def _create_analysis_prompt(self, text: str) -> str:
        """Создает промпт для AI анализа."""
        return f"""Проанализируй договор аренды жилья и найди потенциальные проблемы и подвохи.

ДОГОВОР:
{text[:5000]}  # Ограничиваем размер для экономии токенов

{self._get_analysis_instructions()}"""

    def _get_analysis_instructions(self) -> str:
        """Возвращает инструкции для анализа договора."""
        return """Проанализируй договор и верни результат СТРОГО в формате JSON:
{
    "overall_risk": "low/medium/high",
    "summary": "Краткое резюме на 2-3 предложения",
    "issues": [
        {{
            "title": "Название проблемы",
            "description": "Подробное описание",
            "risk_level": "low/medium/high",
            "section": "Раздел договора (опционально)",
            "recommendation": "Что делать"
        }}
    ],
    "positive_points": ["Положительный момент 1", "Положительный момент 2"],
    "recommendations": ["Рекомендация 1", "Рекомендация 2"],
    "key_terms": {{
        "rent_amount": "Сумма аренды",
        "deposit": "Залог",
        "term": "Срок аренды",
        "utilities": "Коммунальные платежи",
        "early_termination": "Условия досрочного расторжения"
    }}
}}

Обрати особое внимание на:
1. Завышенные штрафы и неустойки
2. Несправедливые условия расторжения
3. Скрытые платежи и комиссии
4. Ограничения прав арендатора
5. Отсутствие важных пунктов (ответственность сторон, форс-мажор)
6. Неясные формулировки
7. Условия возврата залога

Отвечай на русском языке. Будь объективным и конкретным."""

    def _parse_ai_response(self, response: str) -> ContractAnalysisResult:
        """Парсит ответ AI."""
        try:
            # Пытаемся извлечь JSON из ответа
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response)

            # Конвертируем в наши структуры данных
            issues = []
            for issue_data in data.get('issues', []):
                issues.append(ContractIssue(
                    title=issue_data.get('title', 'Неизвестная проблема'),
                    description=issue_data.get('description', ''),
                    risk_level=RiskLevel(issue_data.get('risk_level', 'medium')),
                    section=issue_data.get('section'),
                    recommendation=issue_data.get('recommendation')
                ))

            return ContractAnalysisResult(
                overall_risk=RiskLevel(data.get('overall_risk', 'medium')),
                summary=data.get('summary', 'Требуется дополнительный анализ'),
                issues=issues,
                positive_points=data.get('positive_points', []),
                recommendations=data.get('recommendations', []),
                key_terms=data.get('key_terms', {})
            )

        except Exception as e:
            self.logger.error(f"Ошибка парсинга ответа AI: {e}")
            # Возвращаем базовый результат
            return ContractAnalysisResult(
                overall_risk=RiskLevel.MEDIUM,
                summary="Не удалось полностью проанализировать договор. Рекомендуется проконсультироваться с юристом.",
                issues=[],
                positive_points=[],
                recommendations=["Обратитесь к юристу для детальной проверки договора"],
                key_terms={}
            )

    async def _analyze_with_rules(self, text: str) -> ContractAnalysisResult:
        """Анализ на основе правил (без AI)."""
        text_lower = text.lower()
        issues = []
        positive_points = []
        key_terms = {}

        # Проверка на наличие ключевых разделов
        required_sections = {
            'предмет договора': 'Описание арендуемого помещения',
            'срок аренды': 'Период действия договора',
            'арендная плата': 'Размер и порядок оплаты',
            'права и обязанности': 'Права и обязанности сторон',
            'ответственность сторон': 'Штрафы и неустойки',
            'расторжение договора': 'Условия прекращения договора'
        }

        for section, description in required_sections.items():
            if section not in text_lower:
                issues.append(ContractIssue(
                    title=f"Отсутствует раздел: {description}",
                    description=f"В договоре не найден важный раздел '{section}'",
                    risk_level=RiskLevel.MEDIUM,
                    recommendation="Требуйте добавить этот раздел в договор"
                ))

        # Проверка на подозрительные условия
        suspicious_terms = {
            'штраф': self._check_penalties,
            'неустойка': self._check_penalties,
            'пеня': self._check_penalties,
            'комиссия': self._check_commissions,
            'залог': self._check_deposit,
            'досрочное расторжение': self._check_early_termination,
            'выселение': self._check_eviction
        }

        for term, check_func in suspicious_terms.items():
            if term in text_lower:
                issue = check_func(text)
                if issue:
                    issues.append(issue)

        # Поиск положительных моментов
        if 'акт приема-передачи' in text_lower:
            positive_points.append("Предусмотрен акт приема-передачи помещения")

        if 'показания счетчиков' in text_lower:
            positive_points.append("Фиксируются показания счетчиков")

        if 'форс-мажор' in text_lower or 'обстоятельства непреодолимой силы' in text_lower:
            positive_points.append("Прописаны форс-мажорные обстоятельства")

        # Извлечение ключевых условий
        key_terms = self._extract_key_terms(text)

        # Определение общего уровня риска
        high_risk_count = sum(1 for issue in issues if issue.risk_level == RiskLevel.HIGH)
        medium_risk_count = sum(1 for issue in issues if issue.risk_level == RiskLevel.MEDIUM)

        if high_risk_count > 2 or (high_risk_count > 0 and medium_risk_count > 3):
            overall_risk = RiskLevel.HIGH
        elif high_risk_count > 0 or medium_risk_count > 2:
            overall_risk = RiskLevel.MEDIUM
        else:
            overall_risk = RiskLevel.LOW

        # Формирование резюме
        if overall_risk == RiskLevel.HIGH:
            summary = "Договор содержит серьезные риски. Настоятельно рекомендуется консультация юриста."
        elif overall_risk == RiskLevel.MEDIUM:
            summary = "Договор требует внимательного изучения. Есть спорные моменты."
        else:
            summary = "Договор выглядит стандартным, но требует внимательного прочтения."

        # Рекомендации
        recommendations = []
        if not positive_points:
            recommendations.append("Требуйте добавить акт приема-передачи помещения")

        if high_risk_count > 0:
            recommendations.append("Обсудите выявленные риски с арендодателем")
            recommendations.append("Рассмотрите возможность консультации с юристом")

        recommendations.append("Сохраните все документы и переписку")
        recommendations.append("Фотографируйте состояние квартиры при заселении")

        return ContractAnalysisResult(
            overall_risk=overall_risk,
            summary=summary,
            issues=issues,
            positive_points=positive_points,
            recommendations=recommendations,
            key_terms=key_terms
        )

    def _check_penalties(self, text: str) -> Optional[ContractIssue]:
        """Проверка штрафов и неустоек."""
        import re

        # Ищем упоминания больших штрафов
        penalty_patterns = [
            r'штраф.*?(\d+)\s*(?:%|процент)',
            r'неустойк.*?(\d+)\s*(?:%|процент)',
            r'пен.*?(\d+)\s*(?:%|процент)',
            r'штраф.*?(\d+\s*\d+)\s*(?:руб|₽)',
            r'неустойк.*?(\d+\s*\d+)\s*(?:руб|₽)'
        ]

        for pattern in penalty_patterns:
            matches = re.findall(pattern, text.lower())
            for match in matches:
                amount = int(re.sub(r'\D', '', match))
                if '%' in text and amount > 1:  # Больше 1% в день - подозрительно
                    return ContractIssue(
                        title="Завышенные штрафы",
                        description=f"Обнаружены высокие штрафы/неустойки: {amount}%",
                        risk_level=RiskLevel.HIGH,
                        recommendation="Требуйте снизить размер штрафов до разумных пределов (0.1-0.5% в день)"
                    )
                elif amount > 50000:  # Фиксированный штраф больше 50000 руб
                    return ContractIssue(
                        title="Крупные штрафы",
                        description=f"Установлены крупные фиксированные штрафы: {amount} руб",
                        risk_level=RiskLevel.MEDIUM,
                        recommendation="Обсудите необходимость таких больших штрафов"
                    )

        return None

    def _check_commissions(self, text: str) -> Optional[ContractIssue]:
        """Проверка комиссий."""
        if 'комиссия' in text.lower() and 'агент' not in text.lower():
            return ContractIssue(
                title="Дополнительные комиссии",
                description="В договоре упоминаются комиссии, не связанные с агентским вознаграждением",
                risk_level=RiskLevel.MEDIUM,
                recommendation="Уточните все дополнительные платежи"
            )
        return None

    def _check_deposit(self, text: str) -> Optional[ContractIssue]:
        """Проверка условий залога."""
        text_lower = text.lower()

        if 'залог' in text_lower:
            if 'не возвращается' in text_lower or 'удерживается' in text_lower:
                return ContractIssue(
                    title="Невозвратный залог",
                    description="Обнаружены условия невозврата залога",
                    risk_level=RiskLevel.HIGH,
                    recommendation="Залог должен возвращаться при отсутствии ущерба"
                )

            if 'условия возврата' not in text_lower and 'возврат залога' not in text_lower:
                return ContractIssue(
                    title="Нет условий возврата залога",
                    description="В договоре не прописаны четкие условия возврата залога",
                    risk_level=RiskLevel.MEDIUM,
                    recommendation="Требуйте прописать условия и сроки возврата залога"
                )

        return None

    def _check_early_termination(self, text: str) -> Optional[ContractIssue]:
        """Проверка условий досрочного расторжения."""
        text_lower = text.lower()

        if 'досрочное расторжение' in text_lower:
            if 'только арендодатель' in text_lower or 'по инициативе арендодателя' in text_lower:
                return ContractIssue(
                    title="Одностороннее расторжение",
                    description="Только арендодатель может расторгнуть договор досрочно",
                    risk_level=RiskLevel.HIGH,
                    recommendation="Требуйте равных прав на досрочное расторжение"
                )

            if 'без объяснения причин' in text_lower:
                return ContractIssue(
                    title="Расторжение без причин",
                    description="Арендодатель может расторгнуть договор без объяснения причин",
                    risk_level=RiskLevel.HIGH,
                    recommendation="Требуйте указать конкретные основания для расторжения"
                )

        return None

    def _check_eviction(self, text: str) -> Optional[ContractIssue]:
        """Проверка условий выселения."""
        text_lower = text.lower()

        if 'выселение' in text_lower:
            import re
            days_pattern = r'выселение.*?(\d+)\s*(?:дн|день|дня|дней)'
            matches = re.findall(days_pattern, text_lower)

            for match in matches:
                days = int(match)
                if days < 30:
                    return ContractIssue(
                        title="Короткий срок выселения",
                        description=f"Срок для выселения всего {days} дней",
                        risk_level=RiskLevel.HIGH,
                        recommendation="По закону минимальный срок предупреждения - 3 месяца"
                    )

        return None

    def _extract_key_terms(self, text: str) -> Dict[str, str]:
        """Извлечение ключевых условий договора."""
        import re
        key_terms = {}

        # Поиск суммы аренды
        rent_patterns = [
            r'арендная плата.*?(\d+\s*\d*)\s*(?:руб|₽)',
            r'ежемесячн.*?оплат.*?(\d+\s*\d*)\s*(?:руб|₽)',
            r'стоимость.*?аренд.*?(\d+\s*\d*)\s*(?:руб|₽)'
        ]

        for pattern in rent_patterns:
            match = re.search(pattern, text.lower())
            if match:
                key_terms['rent_amount'] = f"{match.group(1)} руб/мес"
                break

        # Поиск залога
        deposit_pattern = r'залог.*?(\d+\s*\d*)\s*(?:руб|₽)'
        match = re.search(deposit_pattern, text.lower())
        if match:
            key_terms['deposit'] = f"{match.group(1)} руб"

        # Поиск срока аренды
        term_patterns = [
            r'срок.*?договор.*?(\d+)\s*(?:месяц|год|лет)',
            r'договор.*?заключ.*?(\d+)\s*(?:месяц|год|лет)'
        ]

        for pattern in term_patterns:
            match = re.search(pattern, text.lower())
            if match:
                key_terms['term'] = match.group(0)
                break

        # Коммунальные платежи
        if 'коммунальные' in text.lower():
            if 'включены' in text.lower() or 'входят' in text.lower():
                key_terms['utilities'] = "Включены в стоимость"
            elif 'отдельно' in text.lower() or 'дополнительно' in text.lower():
                key_terms['utilities'] = "Оплачиваются отдельно"
            else:
                key_terms['utilities'] = "Упоминаются (уточните условия)"

        return key_terms

    def format_analysis_for_vk(self, result: ContractAnalysisResult) -> str:
        """
        Форматирует результат анализа для отправки в VK.

        Args:
            result: Результат анализа

        Returns:
            Отформатированный текст для VK сообщения
        """
        lines = []

        # Заголовок с уровнем риска
        risk_emoji = {
            RiskLevel.LOW: "🟢",
            RiskLevel.MEDIUM: "🟡",
            RiskLevel.HIGH: "🔴"
        }

        risk_text = {
            RiskLevel.LOW: "НИЗКИЙ РИСК",
            RiskLevel.MEDIUM: "СРЕДНИЙ РИСК",
            RiskLevel.HIGH: "ВЫСОКИЙ РИСК"
        }

        lines.append("📋 РЕЗУЛЬТАТЫ ПРОВЕРКИ ДОГОВОРА")
        lines.append("=" * 30)
        lines.append(f"\n{risk_emoji[result.overall_risk]} Общий уровень риска: {risk_text[result.overall_risk]}")
        lines.append(f"\n📝 {result.summary}")

        # Ключевые условия
        if result.key_terms:
            lines.append("\n📌 КЛЮЧЕВЫЕ УСЛОВИЯ:")
            term_names = {
                'rent_amount': '• Арендная плата',
                'deposit': '• Залог',
                'term': '• Срок аренды',
                'utilities': '• Коммунальные услуги',
                'early_termination': '• Досрочное расторжение'
            }

            for key, value in result.key_terms.items():
                if key in term_names:
                    lines.append(f"{term_names[key]}: {value}")

        # Обнаруженные проблемы
        if result.issues:
            lines.append("\n⚠️ ОБНАРУЖЕННЫЕ ПРОБЛЕМЫ:")

            # Группируем по уровню риска
            high_issues = [i for i in result.issues if i.risk_level == RiskLevel.HIGH]
            medium_issues = [i for i in result.issues if i.risk_level == RiskLevel.MEDIUM]
            low_issues = [i for i in result.issues if i.risk_level == RiskLevel.LOW]

            if high_issues:
                lines.append("\n🔴 Критические:")
                for issue in high_issues[:3]:  # Ограничиваем количество
                    lines.append(f"• {issue.title}")
                    if issue.recommendation:
                        lines.append(f"  → {issue.recommendation}")

            if medium_issues:
                lines.append("\n🟡 Важные:")
                for issue in medium_issues[:3]:
                    lines.append(f"• {issue.title}")

            if low_issues and len(lines) < 30:  # Если есть место
                lines.append("\n🟢 Незначительные:")
                for issue in low_issues[:2]:
                    lines.append(f"• {issue.title}")

        # Положительные моменты
        if result.positive_points:
            lines.append("\n✅ ПОЛОЖИТЕЛЬНЫЕ МОМЕНТЫ:")
            for point in result.positive_points[:3]:
                lines.append(f"• {point}")

        # Рекомендации
        if result.recommendations:
            lines.append("\n💡 РЕКОМЕНДАЦИИ:")
            for rec in result.recommendations[:4]:
                lines.append(f"• {rec}")

        # Дисклеймер
        lines.append("\n" + "─" * 30)
        lines.append("⚖️ Это автоматический анализ. Для полной юридической оценки обратитесь к юристу.")

        return "\n".join(lines)