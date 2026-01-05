import base64
import httpx
import json
from typing import Optional
from datetime import datetime
from io import BytesIO
import PyPDF2

from app.core.config import settings
from app.schemas.document import DocumentMetadata

class AIService:
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.model = settings.OPENROUTER_MODEL
        self.base_url = settings.OPENROUTER_BASE_URL
    
    async def analyze_document(self, file_bytes: bytes, file_type: str, filename: str) -> DocumentMetadata:
        """Analyze document and extract metadata using AI"""
        
        try:
            # Build prompt
            prompt = self._build_extraction_prompt()
            
            # Handle different file types
            if file_type == 'pdf':
                # Extract text from PDF
                print("📄 Извлекаем текст из PDF...")
                text_content = self._extract_text_from_pdf(file_bytes)
                
                if not text_content or len(text_content.strip()) < 50:
                    raise ValueError("PDF содержит слишком мало текста или это отсканированное изображение. Требуется OCR.")
                
                print(f"  ✅ Извлечено {len(text_content)} символов текста")
                print(f"  📝 Первые 200 символов: {text_content[:200]}...")
                
                # Prepare text-only message
                messages = [
                    {
                        "role": "user",
                        "content": f"{prompt}\n\nТекст медицинского документа:\n\n{text_content}"
                    }
                ]
                
            elif file_type in ['jpg', 'jpeg', 'png']:
                # Use vision API for images
                print(f"🖼️ Обрабатываем изображение ({file_type})...")
                
                # Encode file to base64
                file_base64 = base64.b64encode(file_bytes).decode('utf-8')
                
                # Determine content type
                if file_type in ['jpg', 'jpeg']:
                    mime_type = 'image/jpeg'
                else:
                    mime_type = 'image/png'
                
                # Prepare vision message
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{file_base64}"
                                }
                            }
                        ]
                    }
                ]
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
            
            # Call OpenRouter API
            response_data = await self._call_openrouter(messages)
            
            # Parse response
            metadata = self._parse_ai_response(response_data)
            
            return metadata
            
        except Exception as e:
            print(f"❌ AI analysis failed: {str(e)}")
            # Return default metadata on error
            return DocumentMetadata(
                document_type="неизвестно",
                confidence=0.0,
                summary=f"Не удалось автоматически проанализировать документ: {str(e)}"
            )
    
    def _extract_text_from_pdf(self, file_bytes: bytes) -> str:
        """Extract text content from PDF file"""
        try:
            pdf_file = BytesIO(file_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text_parts = []
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            
            full_text = "\n\n".join(text_parts)
            return full_text.strip()
            
        except Exception as e:
            print(f"❌ Ошибка извлечения текста из PDF: {e}")
            raise ValueError(f"Не удалось извлечь текст из PDF: {str(e)}")
    
    def _build_extraction_prompt(self) -> str:
        return """Проанализируй этот медицинский документ и извлеки следующую информацию в формате JSON.

# ОБЯЗАТЕЛЬНАЯ СТРУКТУРА JSON:

{
  "document_type": "ОБЯЗАТЕЛЬНО - один из 5 типов",
  "document_subtype": "условно обязательно",
  "research_area": "только для инструментальных исследований",
  "specialties": ["массив специальностей"],
  "document_date": "YYYY-MM-DD",
  "patient_name": "Фамилия И.О.",
  "medical_facility": "название учреждения",
  "document_language": "ru|en",
  "confidence": 0.95,
  "summary": "краткое содержание"
}

# ТИПЫ ДОКУМЕНТОВ (выбери ОДИН из 5):

1. "Прием врача" - амбулаторный прием, консультация, медицинское заключение врача
2. "Результаты анализа" - лабораторные анализы любого типа
3. "Инструментальное исследование" - УЗИ, МРТ, КТ, рентген, маммография
4. "Функциональная диагностика" - ЭКГ, ЭЭГ, холтер, спирометрия, ФГДС, колоноскопия
5. "Другое" - если не подходит ни под одну категорию

# ПРАВИЛА ЗАПОЛНЕНИЯ ПО ТИПАМ:

## "Прием врача":
- specialties: ["Кардиология", "Терапия"] - ОБЯЗАТЕЛЬНО массив (минимум 1)
- document_subtype: null
- research_area: null

Справочник специальностей: Терапия, Кардиология, Неврология, Гастроэнтерология, Эндокринология, Урология, Оториноларингология (ЛОР), Офтальмология, Травматология и ортопедия, Дерматология, Инфекционные болезни, Ревматология, Пульмонология, Нефрология, Онкология, Хирургия, Акушерство и гинекология, Педиатрия, Психиатрия, Другая специальность

## "Результаты анализа":
- document_subtype: "Общий анализ крови" - ОБЯЗАТЕЛЬНО
- specialties: null
- research_area: null

Подтипы: Общий анализ крови, Биохимический анализ крови, Общий анализ мочи, Анализ кала, Бактериологический анализ, Серологический анализ, Гистологическое исследование, Цитологическое исследование, Иммунологический анализ, Гормональный анализ, Генетический анализ, Другой анализ

## "Инструментальное исследование":
- document_subtype: "УЗИ" - ОБЯЗАТЕЛЬНО
- research_area: "Брюшная полость" - рекомендуется
- specialties: null

Подтипы: УЗИ, МРТ, КТ, Рентген, Маммография, Флюорография, Ангиография, Другое исследование

Области для УЗИ: Брюшная полость, Щитовидная железа, Молочные железы, Органы малого таза, Сердце (ЭхоКГ), Сосуды, Суставы, Мягкие ткани, Другая область

Области для МРТ/КТ: Головной мозг, Позвоночник, Брюшная полость, Грудная клетка, Суставы, Мягкие ткани, Сосуды, Другая область

Области для Рентген: Грудная клетка, Позвоночник, Суставы, Кости конечностей, Черепа, Другая область

## "Функциональная диагностика":
- document_subtype: "ЭКГ (электрокардиография)" - ОБЯЗАТЕЛЬНО
- specialties: null
- research_area: null

Подтипы: ЭКГ (электрокардиография), ЭЭГ (электроэнцефалография), Холтер-мониторирование, Суточный мониторинг АД, Спирометрия, Велоэргометрия, ФГДС (фиброгастродуоденоскопия), Колоноскопия, Бронхоскопия, Другая функциональная диагностика

## "Другое":
- Все дополнительные параметры опциональны
- confidence должна быть низкой (<0.5)

# ОБЩИЕ ПРАВИЛА:

1. document_type - ВСЕГДА ОБЯЗАТЕЛЬНО, используй точное название из списка выше
2. Дата документа - это дата процедуры/приема, НЕ дата печати
3. Формат ФИО: "Иванов И.И." (с точками)
4. Специальности (specialties) - СУЩЕСТВИТЕЛЬНЫЕ: "Кардиология", а НЕ "Кардиолог"
5. Если информация не найдена - используй null
6. confidence (0.0-1.0) - твоя уверенность в классификации
7. document_language - код языка ("ru", "en")

# ВАЖНО:
- Отвечай ТОЛЬКО валидным JSON
- Без дополнительного текста
- Проверь, что структура соответствует типу документа"""
    
    async def _call_openrouter(self, messages: list) -> dict:
        """Make API call to OpenRouter"""
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 2000,
            "temperature": 0.1  # Low temperature for consistent extraction
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "MedHistory"
        }
        
        # Debug logging
        print(f"🔍 OpenRouter Request:")
        print(f"  URL: {self.base_url}")
        print(f"  Model: {self.model}")
        print(f"  API Key: {self.api_key[:10]}...{self.api_key[-10:]}")
        print(f"  Message content types: {[type(m['content']) for m in messages]}")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    json=payload
                )
                
                # Log response details
                print(f"📥 OpenRouter Response:")
                print(f"  Status: {response.status_code}")
                print(f"  Response: {response.text[:500]}")
                
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                print(f"❌ HTTP Error: {e.response.status_code}")
                print(f"   Response body: {e.response.text}")
                raise
            except Exception as e:
                print(f"❌ Request Error: {str(e)}")
                raise
    
    def _parse_ai_response(self, response_data: dict) -> DocumentMetadata:
        """Parse AI response and create DocumentMetadata"""
        
        try:
            # Extract content from response
            content = response_data["choices"][0]["message"]["content"]
            
            # Parse JSON from content
            # Sometimes the model wraps JSON in markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            data = json.loads(content)
            
            # Create DocumentMetadata object with new structure
            metadata = DocumentMetadata(
                # PostgreSQL fields
                document_type=data.get("document_type", "Другое"),
                document_date=data.get("document_date"),
                patient_name=data.get("patient_name"),
                medical_facility=data.get("medical_facility"),
                
                # MongoDB classification fields
                document_subtype=data.get("document_subtype"),
                research_area=data.get("research_area"),
                specialties=data.get("specialties"),
                document_language=data.get("document_language", "ru"),
                confidence=data.get("confidence", 0.5),
                
                # MongoDB extracted_data fields
                summary=data.get("summary")
            )
            
            return metadata
            
        except Exception as e:
            print(f"❌ Error parsing AI response: {str(e)}")
            print(f"Response content: {response_data}")
            raise
    
    async def generate_report_content(self, documents: list, filters: dict) -> str:
        """Generate report content using AI"""
        
        # Prepare context from documents
        context = self._prepare_report_context(documents)
        
        prompt = f"""Создай подробный медицинский отчёт для пациента на основе следующих документов:

{context}

Отчёт должен включать:
1. Общую информацию о пациенте
2. Хронологическую временную линию событий
3. Ключевые результаты анализов и исследований
4. Назначенное лечение и его динамику
5. Резюме текущего состояния здоровья

Формат отчёта должен быть структурированным с четкими заголовками.
Пиши на русском языке.
Будь профессиональным и детальным."""
        
        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        response_data = await self._call_openrouter(messages)
        content = response_data["choices"][0]["message"]["content"]
        
        return content
    
    def _prepare_report_context(self, documents: list) -> str:
        """Prepare context from documents for report generation"""
        
        context_parts = []
        
        for doc in documents:
            doc_info = f"""
Дата: {doc.document_date or 'не указана'}
Тип: {doc.document_type or 'не указан'}
Пациент: {doc.patient_name or 'не указан'}
Учреждение: {doc.medical_facility or 'не указано'}
Файл: {doc.original_filename}
"""
            context_parts.append(doc_info)
        
        return "\n---\n".join(context_parts)

    async def extract_lab_results(self, file_bytes: bytes, file_type: str, filename: str) -> dict:
        """Extract laboratory results using a specialized prompt.

        Returns a dict with key "lab_results": list of standardized entries.
        """
        # Build labs prompt
        prompt = self._build_labs_extraction_prompt()

        # Prepare messages similarly to analyze_document
        if file_type == 'pdf':
            text_content = self._extract_text_from_pdf(file_bytes)
            messages = [
                {
                    "role": "user",
                    "content": f"{prompt}\n\nТекст медицинского документа:\n\n{text_content}"
                }
            ]
        elif file_type in ['jpg', 'jpeg', 'png']:
            file_base64 = base64.b64encode(file_bytes).decode('utf-8')
            mime_type = 'image/jpeg' if file_type in ['jpg', 'jpeg'] else 'image/png'
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{file_base64}"}},
                    ],
                }
            ]
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        response_data = await self._call_openrouter(messages)
        return self._parse_labs_response(response_data)

    def _build_labs_extraction_prompt(self) -> str:
        return """Определи, есть ли в документе результаты лабораторных анализов. Если да, извлеки их в JSON по стандартизованной схеме.

Стандартизованный формат:
{
  "lab_results": [
    {
      "test_name": "название анализа (например: гемоглобин, глюкоза)",
      "value": "числовое значение как строка",
      "unit": "единицы измерения (например: г/л, ммоль/л, %)",
      "reference_range": "референсный диапазон как строка (например: 120-160)",
      "flag": "L|N|H|A"  // L ниже нормы, N норма, H выше нормы, A абнормально/критично
    }
  ]
}

Правила:
- Если анализов нет, верни {"lab_results": []}
- test_name на русском языке, как в документе, но без лишнего шума
- value оставляй строкой, не округляй
- ВАЖНО: unit должен точно соответствовать единицам измерения из документа
  * Если указаны проценты (%), обязательно указывай "%" в unit
  * Если указаны абсолютные значения (например, 10*9/л, х10^9/л, г/л), указывай их точно как в документе
  * Разные единицы измерения одного анализа (например, процентные и абсолютные) - это РАЗНЫЕ биомаркеры
  * Не смешивай единицы: если в документе "Лимфоциты 42%" и "Лимфоциты 2.5 10*9/л", это две отдельные записи
- Если единиц нет, используй null
- Если референс нет, используй null
- Определи flag исходя из референсного диапазона, если он указан
- Отвечай ТОЛЬКО валидным JSON

Примеры правильного извлечения:
- "Лимфоциты 42%" → {"test_name": "Лимфоциты", "value": "42", "unit": "%", ...}
- "Лимфоциты 2.5 10*9/л" → {"test_name": "Лимфоциты", "value": "2.5", "unit": "10*9/л", ...}
- "Гемоглобин 145 г/л" → {"test_name": "Гемоглобин", "value": "145", "unit": "г/л", ...}
- "Гемоглобин 14.5 г/дл" → {"test_name": "Гемоглобин", "value": "14.5", "unit": "г/дл", ...}
"""

    def _parse_labs_response(self, response_data: dict) -> dict:
        try:
            content = response_data["choices"][0]["message"]["content"]
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            data = json.loads(content)

            # Basic normalization
            lab_results = data.get("lab_results") or []
            normalized = []
            for item in lab_results:
                normalized.append({
                    "test_name": item.get("test_name"),
                    "value": item.get("value"),
                    "unit": item.get("unit"),
                    "reference_range": item.get("reference_range"),
                    "flag": item.get("flag"),
                })
            return {"lab_results": normalized}
        except Exception as e:
            print(f"❌ Error parsing labs response: {e}")
            print(f"Response content: {response_data}")
            return {"lab_results": []}

# Create global instance
ai_service = AIService()

