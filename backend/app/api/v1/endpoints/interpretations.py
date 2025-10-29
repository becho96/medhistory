from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.api.deps import get_current_user
from app.db.postgres import get_db
from app.models.user import User
from app.schemas.interpretation import (
    InterpretationCreate,
    InterpretationResponse,
    InterpretationList,
    InterpretationDocumentInfo
)
from app.services.interpretation_service import interpretation_service

router = APIRouter()


@router.post("/", response_model=InterpretationResponse, status_code=status.HTTP_201_CREATED)
async def create_interpretation(
    data: InterpretationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Создать новую AI-интерпретацию для выбранных документов
    
    - **document_ids**: список ID документов для анализа (минимум 1)
    
    Возвращает созданную интерпретацию со статусом 'pending' или 'processing'.
    Обработка происходит асинхронно, результат будет доступен позже.
    """
    try:
        interpretation = await interpretation_service.create_interpretation(
            db=db,
            user_id=current_user.id,
            document_ids=data.document_ids
        )
        
        # Подготовить response с информацией о документах
        return InterpretationResponse(
            id=interpretation.id,
            user_id=interpretation.user_id,
            status=interpretation.status.value,
            interpretation_text=interpretation.interpretation_text,
            error_message=interpretation.error_message,
            created_at=interpretation.created_at,
            updated_at=interpretation.updated_at,
            completed_at=interpretation.completed_at,
            documents=[
                InterpretationDocumentInfo(
                    id=doc.id,
                    original_filename=doc.original_filename,
                    document_date=doc.document_date,
                    document_type=doc.document_type,
                    document_subtype=None
                )
                for doc in interpretation.documents
            ]
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании интерпретации: {str(e)}"
        )


@router.get("/", response_model=InterpretationList)
async def get_interpretations(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить список всех интерпретаций пользователя
    
    - **skip**: количество записей для пропуска (пагинация)
    - **limit**: максимальное количество записей для возврата
    """
    interpretations = await interpretation_service.get_user_interpretations(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )
    
    # Подготовить response с информацией о документах
    items = []
    for interpretation in interpretations:
        response = InterpretationResponse(
            id=interpretation.id,
            user_id=interpretation.user_id,
            status=interpretation.status.value,
            interpretation_text=interpretation.interpretation_text,
            error_message=interpretation.error_message,
            created_at=interpretation.created_at,
            updated_at=interpretation.updated_at,
            completed_at=interpretation.completed_at,
            documents=[
                InterpretationDocumentInfo(
                    id=doc.id,
                    original_filename=doc.original_filename,
                    document_date=doc.document_date,
                    document_type=doc.document_type,
                    document_subtype=None
                )
                for doc in interpretation.documents
            ]
        )
        items.append(response)
    
    # Подсчитать общее количество
    from app.models.interpretation import Interpretation
    from sqlalchemy import select, func
    count_query = select(func.count()).select_from(Interpretation).where(
        Interpretation.user_id == current_user.id
    )
    count_result = await db.execute(count_query)
    total = count_result.scalar()
    
    return InterpretationList(total=total, items=items)


@router.get("/{interpretation_id}", response_model=InterpretationResponse)
async def get_interpretation(
    interpretation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить конкретную интерпретацию по ID
    """
    interpretation = await interpretation_service.get_interpretation_by_id(
        db=db,
        interpretation_id=interpretation_id,
        user_id=current_user.id
    )
    
    if not interpretation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Интерпретация не найдена"
        )
    
    # Подготовить response
    return InterpretationResponse(
        id=interpretation.id,
        user_id=interpretation.user_id,
        status=interpretation.status.value,
        interpretation_text=interpretation.interpretation_text,
        error_message=interpretation.error_message,
        created_at=interpretation.created_at,
        updated_at=interpretation.updated_at,
        completed_at=interpretation.completed_at,
        documents=[
            InterpretationDocumentInfo(
                id=doc.id,
                original_filename=doc.original_filename,
                document_date=doc.document_date,
                document_type=doc.document_type,
                document_subtype=None
            )
            for doc in interpretation.documents
        ]
    )


@router.delete("/{interpretation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_interpretation(
    interpretation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Удалить интерпретацию
    """
    success = await interpretation_service.delete_interpretation(
        db=db,
        interpretation_id=interpretation_id,
        user_id=current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Интерпретация не найдена"
        )
    
    return None

