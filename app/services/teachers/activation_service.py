from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List

from app.cores.token import verify_token
from app.models.users.user import User
from app.models.users.preference import Preference
from app.models.teachers.price import Price
from app.models.teachers.wallet import Wallet
from app.models.teachers.video import Video
from app.models.teachers.document import Document
from app.models.common.status import Status
from app.models.teachers.availability import Availability


async def _get_user_id_from_token(token: str) -> int:
    payload = verify_token(token)
    user_id = payload.get("user_id")
    if not user_id:
        raise ValueError("Token inválido: falta user_id")
    return int(user_id)


async def check_teacher_activation_requirements(db: AsyncSession, token: str) -> Dict:
    """
    Verifica que el docente tenga:
    - Preferencia
    - Precio seleccionado
    - Cartera (wallet) configurada (stripe_account_id presente)
    - Video
    - Documentos
    Retorna un dict con flags y lista de faltantes.
    """
    user_id = await _get_user_id_from_token(token)

    # Preferencia
    pref_q = await db.execute(select(Preference).where(Preference.user_id == user_id))
    has_preference = pref_q.scalars().first() is not None

    # Precio
    price_q = await db.execute(select(Price).where(Price.user_id == user_id))
    has_price = price_q.scalars().first() is not None

    # Wallet (stripe_account_id configurado)
    wallet_q = await db.execute(select(Wallet).where(Wallet.user_id == user_id))
    wallet = wallet_q.scalars().first()
    has_wallet = wallet is not None and bool(wallet.stripe_account_id)

    # Availability (al menos un registro de disponibilidad)
    availability_q = await db.execute(select(Availability.id).where(Availability.user_id == user_id))
    has_availability = availability_q.scalars().first() is not None

    # Video
    video_q = await db.execute(select(Video).where(Video.user_id == user_id))
    has_video = video_q.scalars().first() is not None

    # Documentos
    doc_q = await db.execute(select(Document).where(Document.user_id == user_id))
    has_documents = doc_q.scalars().first() is not None

    missing: List[str] = []
    if not has_preference:
        missing.append("preference")
    if not has_price:
        missing.append("price")
    if not has_wallet:
        missing.append("wallet")
    if not has_availability:
        missing.append("availability")
    if not has_video:
        missing.append("video")
    if not has_documents:
        missing.append("documents")

    return {
        "has_preference": has_preference,
        "has_price": has_price,
        "has_wallet": has_wallet,
        "has_availability": has_availability,
        "has_video": has_video,
        "has_documents": has_documents,
        "missing": missing,
    }


async def activate_teacher_account(db: AsyncSession, token: str) -> Dict:
    """
    Si cumple todos los requisitos, cambia el status del usuario a 'active'.
    Retorna el mismo payload del check (con missing=[]) en data.
    """
    user_id = await _get_user_id_from_token(token)

    check = await check_teacher_activation_requirements(db, token)
    if check["missing"]:
        raise ValueError(
            "No se puede activar la cuenta. Faltan: " + ", ".join(check["missing"]) 
        )

    # Buscar usuario y status 'active'
    user_q = await db.execute(select(User).where(User.id == user_id))
    user = user_q.scalar_one_or_none()
    if not user:
        raise ValueError("Usuario no encontrado")

    status_q = await db.execute(select(Status).where(Status.name == "active"))
    active_status = status_q.scalar_one_or_none()
    if not active_status:
        raise ValueError("No existe el status 'active' en la base de datos")

    user.status_id = active_status.id
    await db.commit()

    return check
