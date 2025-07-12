from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from datetime import datetime

from app.models.users.profile import Profile
from app.schemas.user.profile_schema import ProfileCreateRequest, ProfileUpdateRequest

class ProfileService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_profile(self, profile_data: ProfileCreateRequest) -> Profile:
        """
        Crear un nuevo perfil (async)
        """
        try:
            # Verificar si el usuario ya tiene un perfil
            existing_profile = await self.db.execute(
                select(Profile).where(Profile.user_id == profile_data.user_id)
            )
            existing_profile = existing_profile.scalar_one_or_none()
            
            if existing_profile:
                raise ValueError("El usuario ya tiene un perfil asociado")
            
            # Crear el nuevo perfil
            db_profile = Profile(
                user_id=profile_data.user_id,
                credential=profile_data.credential,
                gender=profile_data.gender,
                sex=profile_data.sex
            )
            
            self.db.add(db_profile)
            await self.db.commit()
            await self.db.refresh(db_profile)
            
            return db_profile
        
        except IntegrityError as e:
            await self.db.rollback()
            raise ValueError(f"Error de integridad: {str(e)}")
        except Exception as e:
            await self.db.rollback()
            raise e
    
    async def get_profile_by_id(self, profile_id: int) -> Optional[Profile]:
        """
        Obtener un perfil por ID (async)
        """
        result = await self.db.execute(
            select(Profile).where(Profile.id == profile_id)
        )
        return result.scalar_one_or_none()
    
    async def get_profile_by_user_id(self, user_id: int) -> Optional[Profile]:
        """
        Obtener un perfil por ID de usuario (async)
        """
        result = await self.db.execute(
            select(Profile).where(Profile.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_all_profiles(self, skip: int = 0, limit: int = 100) -> List[Profile]:
        """
        Obtener todos los perfiles con paginación (async)
        """
        result = await self.db.execute(
            select(Profile).offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def update_profile(self, profile_id: int, profile_data: ProfileUpdateRequest) -> Optional[Profile]:
        """
        Actualizar un perfil existente (async)
        """
        try:
            # Obtener el perfil
            result = await self.db.execute(
                select(Profile).where(Profile.id == profile_id)
            )
            db_profile = result.scalar_one_or_none()
            
            if not db_profile:
                return None
            
            # Actualizar campos
            update_data = profile_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                if hasattr(db_profile, field):
                    setattr(db_profile, field, value)
            
            db_profile.updated_at = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(db_profile)
            
            return db_profile
        
        except IntegrityError as e:
            await self.db.rollback()
            raise ValueError(f"Error de integridad: {str(e)}")
        except Exception as e:
            await self.db.rollback()
            raise e
    
    async def delete_profile(self, profile_id: int) -> bool:
        """
        Eliminar un perfil (async)
        """
        try:
            result = await self.db.execute(
                select(Profile).where(Profile.id == profile_id)
            )
            db_profile = result.scalar_one_or_none()
            
            if not db_profile:
                return False
            
            await self.db.delete(db_profile)
            await self.db.commit()
            
            return True
        
        except Exception as e:
            await self.db.rollback()
            raise e
    
    async def get_profiles_by_gender(self, gender: str) -> List[Profile]:
        """
        Obtener perfiles por género (async)
        """
        result = await self.db.execute(
            select(Profile).where(Profile.gender == gender)
        )
        return result.scalars().all()
    
    async def get_profiles_by_sex(self, sex: str) -> List[Profile]:
        """
        Obtener perfiles por sexo (async)
        """
        result = await self.db.execute(
            select(Profile).where(Profile.sex == sex)
        )
        return result.scalars().all()
    
    async def search_profiles(self, search_term: str) -> List[Profile]:
        """
        Buscar perfiles por credencial (async)
        """
        result = await self.db.execute(
            select(Profile).where(Profile.credential.contains(search_term))
        )
        return result.scalars().all()