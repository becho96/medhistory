#!/usr/bin/env python3
"""
Скрипт для сброса пароля пользователя
"""
import asyncio
from sqlalchemy import select, update
from app.db.postgres import AsyncSessionLocal
from app.models.user import User
from app.core.security import get_password_hash

async def reset_password(email: str, new_password: str):
    """Сброс пароля пользователя"""
    async with AsyncSessionLocal() as db:
        # Проверяем, существует ли пользователь
        query = select(User).where(User.email == email)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"❌ Пользователь с email '{email}' не найден")
            return False
        
        # Хешируем новый пароль
        password_hash = get_password_hash(new_password)
        
        # Обновляем пароль
        user.password_hash = password_hash
        await db.commit()
        
        print(f"✅ Пароль для пользователя '{email}' успешно изменен")
        print(f"   ID: {user.id}")
        print(f"   Имя: {user.full_name}")
        print(f"   Активен: {user.is_active}")
        return True

if __name__ == "__main__":
    # Параметры для сброса
    EMAIL = "becho15rus@gmail.com"
    NEW_PASSWORD = "1234567890"
    
    print(f"🔐 Сброс пароля для {EMAIL}")
    print(f"   Новый пароль: {NEW_PASSWORD}")
    print()
    
    asyncio.run(reset_password(EMAIL, NEW_PASSWORD))
