import uuid
from datetime import date
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, delete
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.family import FamilyRelation, RelationType, INVERSE_RELATIONS
from app.schemas.family import (
    FamilyMemberCreate,
    FamilyMemberUpdate,
    FamilyMemberWithAccess,
    FamilyOwnerInfo,
    SetCredentials,
    RELATION_TYPE_NAMES,
    RelationType as SchemaRelationType,
)
from app.core.security import get_password_hash, verify_password


class FamilyService:
    """Сервис для управления семейными связями"""
    
    @staticmethod
    def _get_relation_display(relation_type: RelationType, custom_relation: Optional[str] = None) -> str:
        """Получить отображаемое название типа связи"""
        if relation_type == RelationType.OTHER and custom_relation:
            return custom_relation
        return RELATION_TYPE_NAMES.get(SchemaRelationType(relation_type.value), relation_type.value)
    
    @staticmethod
    async def get_family_members(
        user_id: uuid.UUID,
        db: AsyncSession
    ) -> List[FamilyMemberWithAccess]:
        """
        Получить всех членов семьи, которыми управляет пользователь.
        """
        # Получаем связи где user является owner
        query = (
            select(FamilyRelation)
            .options(selectinload(FamilyRelation.member))
            .where(FamilyRelation.owner_id == user_id)
            .order_by(FamilyRelation.created_at)
        )
        result = await db.execute(query)
        relations = result.scalars().all()
        
        members = []
        for relation in relations:
            member = relation.member
            members.append(FamilyMemberWithAccess(
                id=member.id,
                full_name=member.full_name,
                birth_date=member.birth_date,
                email=member.email,
                has_credentials=member.has_credentials,
                relation_type=SchemaRelationType(relation.relation_type.value),
                relation_type_display=FamilyService._get_relation_display(
                    relation.relation_type, 
                    relation.custom_relation
                ),
                custom_relation=relation.custom_relation,
                is_active=member.is_active,
                created_at=member.created_at,
                is_owner=True
            ))
        
        return members
    
    @staticmethod
    async def get_family_owners(
        user_id: uuid.UUID,
        db: AsyncSession
    ) -> List[FamilyOwnerInfo]:
        """
        Получить всех пользователей, которые управляют данным пользователем.
        """
        query = (
            select(FamilyRelation)
            .options(selectinload(FamilyRelation.owner))
            .where(FamilyRelation.member_id == user_id)
        )
        result = await db.execute(query)
        relations = result.scalars().all()
        
        owners = []
        for relation in relations:
            owner = relation.owner
            # Получаем обратный тип связи
            inverse_type = INVERSE_RELATIONS.get(relation.relation_type, relation.relation_type)
            owners.append(FamilyOwnerInfo(
                id=owner.id,
                full_name=owner.full_name,
                email=owner.email,
                relation_type=SchemaRelationType(inverse_type.value),
                relation_type_display=FamilyService._get_relation_display(
                    inverse_type, 
                    relation.custom_relation
                ),
            ))
        
        return owners
    
    @staticmethod
    async def get_accessible_profiles(
        user_id: uuid.UUID,
        db: AsyncSession
    ) -> List[FamilyMemberWithAccess]:
        """
        Получить все профили, доступные пользователю (включая свой).
        Используется для переключателя профилей.
        """
        # Получаем данные текущего пользователя
        user_query = select(User).where(User.id == user_id)
        user_result = await db.execute(user_query)
        current_user = user_result.scalar_one_or_none()
        
        if not current_user:
            return []
        
        profiles = []
        
        # Добавляем текущего пользователя
        profiles.append(FamilyMemberWithAccess(
            id=current_user.id,
            full_name=current_user.full_name or "Мой профиль",
            birth_date=current_user.birth_date,
            email=current_user.email,
            has_credentials=current_user.has_credentials,
            relation_type=SchemaRelationType.OTHER,
            relation_type_display="Я",
            custom_relation=None,
            is_active=current_user.is_active,
            created_at=current_user.created_at,
            is_owner=True
        ))
        
        # Добавляем членов семьи
        family_members = await FamilyService.get_family_members(user_id, db)
        profiles.extend(family_members)
        
        return profiles
    
    @staticmethod
    async def create_family_member(
        owner_id: uuid.UUID,
        data: FamilyMemberCreate,
        db: AsyncSession
    ) -> Tuple[User, FamilyRelation]:
        """
        Создать нового члена семьи.
        Создается новый User и связь FamilyRelation.
        """
        # Проверяем, не существует ли уже пользователь с таким email
        if data.email:
            existing_query = select(User).where(User.email == data.email)
            existing_result = await db.execute(existing_query)
            existing_user = existing_result.scalar_one_or_none()
            if existing_user:
                raise ValueError("Пользователь с таким email уже существует. Используйте функцию приглашения.")
        
        # Создаем нового пользователя
        new_user = User(
            full_name=data.full_name,
            birth_date=data.birth_date,
            email=data.email,
            password_hash=None,  # Без пароля, пока не установят
            is_active=True
        )
        db.add(new_user)
        await db.flush()  # Получаем ID
        
        # Создаем связь
        relation = FamilyRelation(
            owner_id=owner_id,
            member_id=new_user.id,
            relation_type=RelationType(data.relation_type.value),
            custom_relation=data.custom_relation
        )
        db.add(relation)
        await db.commit()
        await db.refresh(new_user)
        await db.refresh(relation)
        
        return new_user, relation
    
    @staticmethod
    async def update_family_member(
        owner_id: uuid.UUID,
        member_id: uuid.UUID,
        data: FamilyMemberUpdate,
        db: AsyncSession
    ) -> Optional[User]:
        """
        Обновить информацию о члене семьи.
        Только owner может обновлять.
        """
        # Проверяем, что связь существует и пользователь является owner
        relation_query = select(FamilyRelation).where(
            and_(
                FamilyRelation.owner_id == owner_id,
                FamilyRelation.member_id == member_id
            )
        )
        relation_result = await db.execute(relation_query)
        relation = relation_result.scalar_one_or_none()
        
        if not relation:
            raise PermissionError("У вас нет доступа к этому профилю")
        
        # Получаем пользователя
        user_query = select(User).where(User.id == member_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise ValueError("Пользователь не найден")
        
        # Обновляем данные пользователя
        if data.full_name is not None:
            user.full_name = data.full_name
        if data.birth_date is not None:
            user.birth_date = data.birth_date
        
        # Обновляем данные связи
        if data.relation_type is not None:
            relation.relation_type = RelationType(data.relation_type.value)
        if data.custom_relation is not None:
            relation.custom_relation = data.custom_relation
        
        await db.commit()
        await db.refresh(user)
        
        return user
    
    @staticmethod
    async def set_member_credentials(
        owner_id: uuid.UUID,
        member_id: uuid.UUID,
        credentials: SetCredentials,
        db: AsyncSession
    ) -> User:
        """
        Установить email и пароль для члена семьи.
        После этого он сможет входить самостоятельно.
        """
        # Проверяем права доступа
        relation_query = select(FamilyRelation).where(
            and_(
                FamilyRelation.owner_id == owner_id,
                FamilyRelation.member_id == member_id
            )
        )
        relation_result = await db.execute(relation_query)
        relation = relation_result.scalar_one_or_none()
        
        if not relation:
            raise PermissionError("У вас нет доступа к этому профилю")
        
        # Проверяем, не занят ли email
        email_query = select(User).where(
            and_(
                User.email == credentials.email,
                User.id != member_id
            )
        )
        email_result = await db.execute(email_query)
        if email_result.scalar_one_or_none():
            raise ValueError("Этот email уже используется")
        
        # Получаем и обновляем пользователя
        user_query = select(User).where(User.id == member_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise ValueError("Пользователь не найден")
        
        user.email = credentials.email
        user.password_hash = get_password_hash(credentials.password)
        
        await db.commit()
        await db.refresh(user)
        
        return user
    
    @staticmethod
    async def remove_family_member(
        owner_id: uuid.UUID,
        member_id: uuid.UUID,
        db: AsyncSession
    ) -> bool:
        """
        Удалить члена семьи из списка управляемых.
        Если у члена семьи нет credentials, удаляем и пользователя.
        Если credentials есть, просто удаляем связь.
        """
        # Проверяем права доступа
        relation_query = select(FamilyRelation).where(
            and_(
                FamilyRelation.owner_id == owner_id,
                FamilyRelation.member_id == member_id
            )
        )
        relation_result = await db.execute(relation_query)
        relation = relation_result.scalar_one_or_none()
        
        if not relation:
            raise PermissionError("У вас нет доступа к этому профилю")
        
        # Получаем пользователя
        user_query = select(User).where(User.id == member_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise ValueError("Пользователь не найден")
        
        # Удаляем связь
        await db.delete(relation)
        
        # Проверяем, есть ли другие владельцы у этого пользователя
        other_owners_query = select(FamilyRelation).where(
            and_(
                FamilyRelation.member_id == member_id,
                FamilyRelation.owner_id != owner_id
            )
        )
        other_owners_result = await db.execute(other_owners_query)
        has_other_owners = other_owners_result.scalar_one_or_none() is not None
        
        # Если нет credentials и нет других владельцев, удаляем пользователя
        if not user.has_credentials and not has_other_owners:
            await db.delete(user)
        
        await db.commit()
        return True
    
    @staticmethod
    async def detach_from_owner(
        user_id: uuid.UUID,
        owner_id: uuid.UUID,
        db: AsyncSession
    ) -> bool:
        """
        Отвязаться от владельца (для самостоятельного управления).
        Пользователь должен иметь credentials.
        """
        # Проверяем, что у пользователя есть credentials
        user_query = select(User).where(User.id == user_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise ValueError("Пользователь не найден")
        
        if not user.has_credentials:
            raise ValueError("Для отвязки необходимо сначала установить email и пароль")
        
        # Удаляем связь
        relation_query = select(FamilyRelation).where(
            and_(
                FamilyRelation.owner_id == owner_id,
                FamilyRelation.member_id == user_id
            )
        )
        relation_result = await db.execute(relation_query)
        relation = relation_result.scalar_one_or_none()
        
        if not relation:
            raise ValueError("Связь не найдена")
        
        await db.delete(relation)
        await db.commit()
        
        return True
    
    @staticmethod
    async def invite_existing_user(
        owner_id: uuid.UUID,
        email: str,
        relation_type: RelationType,
        custom_relation: Optional[str],
        db: AsyncSession
    ) -> FamilyRelation:
        """
        Добавить существующего пользователя в семью.
        Пользователь с таким email должен существовать.
        """
        # Находим пользователя по email
        user_query = select(User).where(User.email == email)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise ValueError("Пользователь с таким email не найден")
        
        if user.id == owner_id:
            raise ValueError("Нельзя добавить себя в качестве члена семьи")
        
        # Проверяем, нет ли уже такой связи
        existing_query = select(FamilyRelation).where(
            and_(
                FamilyRelation.owner_id == owner_id,
                FamilyRelation.member_id == user.id
            )
        )
        existing_result = await db.execute(existing_query)
        if existing_result.scalar_one_or_none():
            raise ValueError("Этот пользователь уже добавлен в вашу семью")
        
        # Создаем связь
        relation = FamilyRelation(
            owner_id=owner_id,
            member_id=user.id,
            relation_type=relation_type,
            custom_relation=custom_relation
        )
        db.add(relation)
        await db.commit()
        await db.refresh(relation)
        
        return relation
    
    @staticmethod
    async def check_profile_access(
        user_id: uuid.UUID,
        profile_id: uuid.UUID,
        db: AsyncSession
    ) -> bool:
        """
        Проверить, имеет ли пользователь доступ к профилю.
        Доступ есть если:
        - profile_id == user_id (свой профиль)
        - user_id является owner для profile_id
        """
        if user_id == profile_id:
            return True
        
        relation_query = select(FamilyRelation).where(
            and_(
                FamilyRelation.owner_id == user_id,
                FamilyRelation.member_id == profile_id
            )
        )
        relation_result = await db.execute(relation_query)
        return relation_result.scalar_one_or_none() is not None


family_service = FamilyService()

