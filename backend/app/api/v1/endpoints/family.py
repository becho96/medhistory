from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid

from app.db.postgres import get_db
from app.models.user import User
from app.models.family import RelationType
from app.api.deps import get_current_user
from app.services.family_service import family_service
from app.schemas.family import (
    FamilyMemberCreate,
    FamilyMemberUpdate,
    FamilyMemberResponse,
    FamilyMemberWithAccess,
    FamilyListResponse,
    FamilyOwnerInfo,
    MyFamilyInfo,
    SetCredentials,
    InviteExistingUser,
    DetachFromFamily,
    RELATION_TYPE_NAMES,
    RelationType as SchemaRelationType,
)

router = APIRouter()


@router.get("/profiles", response_model=List[FamilyMemberWithAccess])
async def get_accessible_profiles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить все доступные профили для переключения.
    Включает свой профиль и профили членов семьи.
    """
    return await family_service.get_accessible_profiles(current_user.id, db)


@router.get("/members", response_model=FamilyListResponse)
async def get_family_members(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить список членов семьи, которыми управляет текущий пользователь.
    """
    members = await family_service.get_family_members(current_user.id, db)
    return FamilyListResponse(members=members, total=len(members))


@router.get("/info", response_model=MyFamilyInfo)
async def get_my_family_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить полную информацию о семейных связях пользователя.
    Включает тех, кем пользователь управляет, и тех, кто управляет пользователем.
    """
    managed_by = await family_service.get_family_owners(current_user.id, db)
    managing = await family_service.get_family_members(current_user.id, db)
    
    # Пользователь может отвязаться, если у него есть credentials и им кто-то управляет
    can_detach = current_user.has_credentials and len(managed_by) > 0
    
    return MyFamilyInfo(
        managed_by=managed_by,
        managing=managing,
        can_detach=can_detach
    )


@router.get("/relation-types")
async def get_relation_types():
    """
    Получить список доступных типов отношений.
    """
    return [
        {"value": rt.value, "label": RELATION_TYPE_NAMES[rt]}
        for rt in SchemaRelationType
    ]


@router.post("/members", response_model=FamilyMemberResponse, status_code=status.HTTP_201_CREATED)
async def create_family_member(
    data: FamilyMemberCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Создать нового члена семьи.
    Создается новый пользователь и связь с текущим пользователем.
    """
    try:
        user, relation = await family_service.create_family_member(
            owner_id=current_user.id,
            data=data,
            db=db
        )
        
        return FamilyMemberResponse(
            id=user.id,
            full_name=user.full_name,
            birth_date=user.birth_date,
            email=user.email,
            has_credentials=user.has_credentials,
            relation_type=SchemaRelationType(relation.relation_type.value),
            relation_type_display=RELATION_TYPE_NAMES.get(
                SchemaRelationType(relation.relation_type.value),
                relation.relation_type.value
            ),
            custom_relation=relation.custom_relation,
            is_active=user.is_active,
            created_at=user.created_at
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/members/{member_id}", response_model=FamilyMemberResponse)
async def update_family_member(
    member_id: uuid.UUID,
    data: FamilyMemberUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Обновить информацию о члене семьи.
    """
    try:
        user = await family_service.update_family_member(
            owner_id=current_user.id,
            member_id=member_id,
            data=data,
            db=db
        )
        
        # Получаем обновленную связь
        members = await family_service.get_family_members(current_user.id, db)
        member_info = next((m for m in members if m.id == member_id), None)
        
        if not member_info:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Член семьи не найден")
        
        return FamilyMemberResponse(
            id=user.id,
            full_name=user.full_name,
            birth_date=user.birth_date,
            email=user.email,
            has_credentials=user.has_credentials,
            relation_type=member_info.relation_type,
            relation_type_display=member_info.relation_type_display,
            custom_relation=member_info.custom_relation,
            is_active=user.is_active,
            created_at=user.created_at
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/members/{member_id}/credentials", response_model=FamilyMemberResponse)
async def set_member_credentials(
    member_id: uuid.UUID,
    credentials: SetCredentials,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Установить email и пароль для члена семьи.
    После этого он сможет входить самостоятельно.
    """
    try:
        user = await family_service.set_member_credentials(
            owner_id=current_user.id,
            member_id=member_id,
            credentials=credentials,
            db=db
        )
        
        # Получаем информацию о связи
        members = await family_service.get_family_members(current_user.id, db)
        member_info = next((m for m in members if m.id == member_id), None)
        
        if not member_info:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Член семьи не найден")
        
        return FamilyMemberResponse(
            id=user.id,
            full_name=user.full_name,
            birth_date=user.birth_date,
            email=user.email,
            has_credentials=user.has_credentials,
            relation_type=member_info.relation_type,
            relation_type_display=member_info.relation_type_display,
            custom_relation=member_info.custom_relation,
            is_active=user.is_active,
            created_at=user.created_at
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_family_member(
    member_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Удалить члена семьи из списка управляемых.
    Если у него нет учетных данных для самостоятельного входа - удаляется полностью.
    """
    try:
        await family_service.remove_family_member(
            owner_id=current_user.id,
            member_id=member_id,
            db=db
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/invite", response_model=FamilyMemberResponse)
async def invite_existing_user(
    data: InviteExistingUser,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Добавить существующего пользователя в семью по email.
    """
    try:
        relation = await family_service.invite_existing_user(
            owner_id=current_user.id,
            email=data.email,
            relation_type=RelationType(data.relation_type.value),
            custom_relation=data.custom_relation,
            db=db
        )
        
        # Получаем обновленный список членов семьи
        members = await family_service.get_family_members(current_user.id, db)
        member_info = next((m for m in members if m.id == relation.member_id), None)
        
        if not member_info:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при добавлении")
        
        return FamilyMemberResponse(
            id=member_info.id,
            full_name=member_info.full_name,
            birth_date=member_info.birth_date,
            email=member_info.email,
            has_credentials=member_info.has_credentials,
            relation_type=member_info.relation_type,
            relation_type_display=member_info.relation_type_display,
            custom_relation=member_info.custom_relation,
            is_active=member_info.is_active,
            created_at=member_info.created_at
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/detach", status_code=status.HTTP_204_NO_CONTENT)
async def detach_from_family(
    data: DetachFromFamily,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Отвязаться от владельца профиля.
    Пользователь должен иметь email и пароль для самостоятельного входа.
    """
    try:
        await family_service.detach_from_owner(
            user_id=current_user.id,
            owner_id=data.owner_id,
            db=db
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/check-access/{profile_id}")
async def check_profile_access(
    profile_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Проверить, имеет ли текущий пользователь доступ к указанному профилю.
    """
    has_access = await family_service.check_profile_access(
        user_id=current_user.id,
        profile_id=profile_id,
        db=db
    )
    return {"has_access": has_access, "profile_id": str(profile_id)}

