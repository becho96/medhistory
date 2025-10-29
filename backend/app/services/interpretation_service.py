import json
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from datetime import datetime
from uuid import UUID

from app.models.interpretation import Interpretation, InterpretationStatus
from app.models.document import Document
from app.db.mongodb import get_metadata_collection
from app.services.ai_service import ai_service


class InterpretationService:
    """Сервис для создания и управления AI-интерпретациями результатов анализов"""
    
    async def create_interpretation(
        self, 
        db: AsyncSession, 
        user_id: UUID, 
        document_ids: List[UUID]
    ) -> Interpretation:
        """Создать новую интерпретацию для выбранных документов"""
        
        # Проверка наличия всех документов и что они принадлежат пользователю
        query = select(Document).where(
            and_(
                Document.id.in_(document_ids),
                Document.user_id == user_id
            )
        )
        result = await db.execute(query)
        documents = result.scalars().all()
        
        if len(documents) != len(document_ids):
            raise ValueError("Некоторые документы не найдены или не принадлежат пользователю")
        
        # Проверка на дубликат (те же самые документы)
        existing = await self._find_existing_interpretation(db, user_id, document_ids)
        if existing:
            raise ValueError(f"Интерпретация для этого набора документов уже существует (ID: {existing.id})")
        
        # Создать новую интерпретацию
        interpretation = Interpretation(
            user_id=user_id,
            status=InterpretationStatus.pending
        )
        
        # Добавить связи с документами
        interpretation.documents = list(documents)
        
        db.add(interpretation)
        await db.commit()
        await db.refresh(interpretation)
        
        # Запустить асинхронную обработку
        await self._process_interpretation(db, interpretation)
        
        # Перезагрузить интерпретацию с документами для возврата
        query = select(Interpretation).where(
            Interpretation.id == interpretation.id
        ).options(selectinload(Interpretation.documents))
        result = await db.execute(query)
        interpretation = result.scalar_one()
        
        return interpretation
    
    async def _find_existing_interpretation(
        self, 
        db: AsyncSession, 
        user_id: UUID, 
        document_ids: List[UUID]
    ) -> Interpretation | None:
        """Найти существующую интерпретацию для того же набора документов"""
        
        # Получить все интерпретации пользователя с eager loading документов
        query = select(Interpretation).where(
            Interpretation.user_id == user_id
        ).options(selectinload(Interpretation.documents))
        result = await db.execute(query)
        interpretations = result.scalars().all()
        
        # Проверить каждую интерпретацию
        doc_ids_set = set(document_ids)
        for interp in interpretations:
            interp_doc_ids = set(doc.id for doc in interp.documents)
            if interp_doc_ids == doc_ids_set:
                return interp
        
        return None
    
    async def _process_interpretation(self, db: AsyncSession, interpretation: Interpretation):
        """Обработать интерпретацию с помощью AI"""
        
        try:
            # Обновить статус на processing
            interpretation.status = InterpretationStatus.processing
            await db.commit()
            
            # Перезагрузить интерпретацию с документами
            query = select(Interpretation).where(
                Interpretation.id == interpretation.id
            ).options(selectinload(Interpretation.documents))
            result = await db.execute(query)
            interpretation = result.scalar_one()
            
            # Собрать данные из документов и MongoDB
            documents_data = await self._collect_documents_data(db, interpretation.documents)
            
            # Сгенерировать интерпретацию с помощью AI
            interpretation_text = await self._generate_interpretation(documents_data)
            
            # Обновить интерпретацию
            interpretation.status = InterpretationStatus.completed
            interpretation.interpretation_text = interpretation_text
            interpretation.completed_at = datetime.utcnow()
            
            await db.commit()
            
        except Exception as e:
            print(f"❌ Ошибка при обработке интерпретации {interpretation.id}: {str(e)}")
            interpretation.status = InterpretationStatus.failed
            interpretation.error_message = str(e)
            await db.commit()
    
    async def _collect_documents_data(self, db: AsyncSession, documents: List[Document]) -> List[Dict[str, Any]]:
        """Собрать все данные из документов для интерпретации"""
        
        documents_data = []
        metadata_collection = get_metadata_collection()
        
        for doc in documents:
            doc_data = {
                "id": str(doc.id),
                "original_filename": doc.original_filename,
                "document_type": doc.document_type,
                "document_date": doc.document_date.isoformat() if doc.document_date else None,
                "patient_name": doc.patient_name,
                "medical_facility": doc.medical_facility,
                "lab_results": [],
                "summary": None,
                "document_subtype": None,
                "specialties": None,
            }
            
            # Получить дополнительные данные из MongoDB
            if doc.mongodb_metadata_id:
                try:
                    from bson import ObjectId
                    mongo_data = metadata_collection.find_one({"_id": ObjectId(doc.mongodb_metadata_id)})
                    if mongo_data:
                        # Классификация
                        classification = mongo_data.get("classification", {})
                        doc_data["document_subtype"] = classification.get("document_subtype")
                        doc_data["specialties"] = classification.get("specialties")
                        
                        # Извлеченные данные
                        extracted_data = mongo_data.get("extracted_data", {})
                        doc_data["summary"] = extracted_data.get("summary")
                        doc_data["lab_results"] = extracted_data.get("lab_results", [])
                except Exception as e:
                    print(f"⚠️ Не удалось получить данные из MongoDB для документа {doc.id}: {str(e)}")
            
            documents_data.append(doc_data)
        
        # Сортировать по дате
        documents_data.sort(key=lambda x: x["document_date"] or "")
        
        return documents_data
    
    async def _generate_interpretation(self, documents_data: List[Dict[str, Any]]) -> str:
        """Сгенерировать AI-интерпретацию на основе данных документов"""
        
        # Подготовить промпт для AI
        prompt = self._build_interpretation_prompt(documents_data)
        
        # Вызвать AI через существующий сервис
        messages = [
            {
                "role": "system",
                "content": """Ты медицинский AI-ассистент, специализирующийся на интерпретации результатов анализов.
Твоя задача - предоставить понятное для пациента объяснение результатов анализов.

ВАЖНЫЕ ПРАВИЛА:
1. Используй осторожные, не категоричные формулировки
2. НЕ ставь диагнозы
3. Используй понятный для пациента язык
4. Будь эмпатичным
5. При критических отклонениях настоятельно рекомендуй обратиться к врачу
6. Если показатели в норме - явно укажи на это для снижения тревожности"""
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        response_data = await ai_service._call_openrouter(messages)
        interpretation_text = response_data["choices"][0]["message"]["content"]
        
        return interpretation_text
    
    def _build_interpretation_prompt(self, documents_data: List[Dict[str, Any]]) -> str:
        """Построить промпт для генерации интерпретации"""
        
        # Подсчитать статистику
        total_docs = len(documents_data)
        docs_with_labs = sum(1 for doc in documents_data if doc.get("lab_results"))
        total_lab_results = sum(len(doc.get("lab_results", [])) for doc in documents_data)
        
        # Собрать информацию о документах
        docs_info = []
        for i, doc in enumerate(documents_data, 1):
            doc_info = f"\n### Документ {i}"
            doc_info += f"\n- Файл: {doc['original_filename']}"
            doc_info += f"\n- Тип: {doc.get('document_type', 'не указан')}"
            if doc.get('document_subtype'):
                doc_info += f"\n- Подтип: {doc['document_subtype']}"
            if doc.get('document_date'):
                doc_info += f"\n- Дата: {doc['document_date']}"
            if doc.get('medical_facility'):
                doc_info += f"\n- Учреждение: {doc['medical_facility']}"
            
            # Результаты анализов
            lab_results = doc.get("lab_results", [])
            if lab_results:
                doc_info += f"\n\n**Результаты анализов ({len(lab_results)} показателей):**"
                for lab in lab_results:
                    test_name = lab.get("test_name", "Неизвестный показатель")
                    value = lab.get("value", "?")
                    unit = lab.get("unit") or ""
                    ref_range = lab.get("reference_range") or "не указан"
                    flag = lab.get("flag") or "N"
                    
                    flag_text = {
                        "L": "⬇️ Ниже нормы",
                        "H": "⬆️ Выше нормы",
                        "A": "⚠️ Критично",
                        "N": "✅ Норма"
                    }.get(flag, "")
                    
                    doc_info += f"\n- {test_name}: {value} {unit} (референс: {ref_range}) {flag_text}"
            
            # Краткое содержание
            if doc.get("summary"):
                doc_info += f"\n\n**Краткое содержание:**\n{doc['summary']}"
            
            docs_info.append(doc_info)
        
        # Собрать полный промпт
        prompt = f"""Проанализируй следующие медицинские документы пациента и предоставь интерпретацию:

## Общая информация
- Всего документов: {total_docs}
- Документов с результатами анализов: {docs_with_labs}
- Общее количество показателей: {total_lab_results}

## Документы
{"".join(docs_info)}

---

Предоставь подробную интерпретацию в следующей структуре:

1. **Общая оценка** - краткое резюме о состоянии показателей (норма/требует внимания/требует консультации врача)

2. **Анализ показателей** - разбор по категориям или системам организма:
   - Какие показатели в норме
   - Какие показатели отклонены (с указанием степени отклонения)
   - Что могут означать эти отклонения (в общих чертах, БЕЗ диагнозов)

3. **Динамика** (если есть несколько анализов во времени):
   - Какие показатели улучшились
   - Какие показатели ухудшились
   - Какие остались стабильными

4. **Рекомендации**:
   - Общие рекомендации (без назначения лечения!)
   - Нужно ли обратиться к врачу и к какому специалисту
   - На что обратить внимание

5. **Важное напоминание** - обязательно укажи дисклеймер о том, что:
   - Это не заменяет консультацию врача
   - Интерпретация носит информационный характер
   - Рекомендуется обсудить результаты с лечащим врачом

Пиши на русском языке, простым и понятным для пациента языком.
Если показатели в норме - обязательно успокой пациента и явно укажи на это.
При критических отклонениях настоятельно рекомендуй немедленно обратиться к врачу."""
        
        return prompt
    
    async def get_user_interpretations(
        self, 
        db: AsyncSession, 
        user_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Interpretation]:
        """Получить список интерпретаций пользователя"""
        
        query = select(Interpretation)\
            .where(Interpretation.user_id == user_id)\
            .options(selectinload(Interpretation.documents))\
            .order_by(Interpretation.created_at.desc())\
            .offset(skip)\
            .limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_interpretation_by_id(
        self, 
        db: AsyncSession, 
        interpretation_id: UUID, 
        user_id: UUID
    ) -> Interpretation | None:
        """Получить интерпретацию по ID"""
        
        query = select(Interpretation).where(
            and_(
                Interpretation.id == interpretation_id,
                Interpretation.user_id == user_id
            )
        ).options(selectinload(Interpretation.documents))
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def delete_interpretation(
        self, 
        db: AsyncSession, 
        interpretation_id: UUID, 
        user_id: UUID
    ) -> bool:
        """Удалить интерпретацию"""
        
        interpretation = await self.get_interpretation_by_id(db, interpretation_id, user_id)
        if not interpretation:
            return False
        
        await db.delete(interpretation)
        await db.commit()
        return True


# Create global instance
interpretation_service = InterpretationService()

