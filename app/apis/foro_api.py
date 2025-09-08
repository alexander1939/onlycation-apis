from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Query
from typing import Optional

from app.apis.deps import auth_required, get_db

from app.services.foro.foro_service import create_foro, update_my_foro, get_my_foros, get_recent_foros
from app.schemas.foro.foro_schema import (
    ForoCreateRequest, ForoCreateResponse, ForoCreateData,
    ForoUpdateMeRequest, ForoUpdateResponse, ForoUpdateData, ForoListResponse, ForoListData
)

router = APIRouter()
security = HTTPBearer()


# -----------------------------
# Create Foro
# -----------------------------
@router.post("/create_foro/", response_model=ForoCreateResponse, dependencies=[Depends(auth_required)])
async def create_foro_route(
    foro_data: ForoCreateRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    token = credentials.credentials
    foro = await create_foro(db, token, foro_data)

    return ForoCreateResponse(
        success=True,
        message="Foro creado exitosamente",
        data=ForoCreateData.model_validate(foro)
    )

# -----------------------------
# Update My Foro
# -----------------------------
@router.put("/update/me_foro/", response_model=ForoUpdateResponse, dependencies=[Depends(auth_required)])
async def update_my_foro_route(
    foro_data: ForoUpdateMeRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    token = credentials.credentials
    foro = await update_my_foro(db, token, foro_data)

    return ForoUpdateResponse(
        success=True,
        message="Foro actualizado exitosamente",
        data=ForoUpdateData.model_validate(foro)
    )





@router.get("/my-foros/", response_model=ForoListResponse,dependencies=[Depends(auth_required)])
async def get_my_foros_route(
    offset: int = Query(0, ge=0),
    limit: int = Query(6, ge=1, le=50),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene los foros del usuario autenticado"""
    token = credentials.credentials
    result = await get_my_foros(db, token, offset, limit)
    
    return ForoListResponse(
        success=True,
        message="Mis foros obtenidos exitosamente",
        data=[ForoListData.model_validate(item) for item in result["items"]],
        total=result["total"],
        offset=result["offset"],
        limit=result["limit"],
        has_more=result["has_more"]
    )



@router.get("/recent-foros/", response_model=ForoListResponse,dependencies=[Depends(auth_required)])
async def get_recent_foros_route(
    offset: int = Query(0, ge=0),
    limit: int = Query(6, ge=1, le=50),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene los foros más recientes"""
    token = credentials.credentials
    result = await get_recent_foros(db, token, offset, limit)  
    
    return ForoListResponse(
        success=True,
        message="Foros recientes obtenidos exitosamente",
        data=[ForoListData.model_validate(item) for item in result["items"]],
        total=result["total"],
        offset=result["offset"],
        limit=result["limit"],
        has_more=result["has_more"]
    )



from app.services.foro.foro_comment_service import create_foro_comment, update_my_foro_comment, delete_my_foro_comment, get_my_comments, get_recent_comments
from app.schemas.foro.foro_comment_schema import (
    ForoCommentCreateRequest, ForoCommentCreateResponse, ForoCommentCreateData,
    ForoCommentUpdateMeRequest, ForoCommentUpdateResponse, ForoCommentUpdateData,
    ForoCommentDeleteResponse, ForoCommentDeleteMeRequest, ForoCommentListData, ForoCommentListResponse
)

# -----------------------------
# Create Comment
# -----------------------------
@router.post("/create_foro_comment/", response_model=ForoCommentCreateResponse, dependencies=[Depends(auth_required)])
async def create_foro_comment_route(
    comment_data: ForoCommentCreateRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    token = credentials.credentials
    comment = await create_foro_comment(db, token, comment_data)
    return ForoCommentCreateResponse(
        success=True,
        message="Comentario creado exitosamente",
        data=ForoCommentCreateData.model_validate(comment)
    )

# -----------------------------
# Update My Comment
# -----------------------------
@router.put("/update/me_foro_comment/", response_model=ForoCommentUpdateResponse, dependencies=[Depends(auth_required)])
async def update_my_foro_comment_route(
    comment_data: ForoCommentUpdateMeRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    token = credentials.credentials
    comment = await update_my_foro_comment(db, token, comment_data)
    return ForoCommentUpdateResponse(
        success=True,
        message="Comentario actualizado exitosamente",
        data=ForoCommentUpdateData.model_validate(comment)
    )

# -----------------------------
# Delete My Comment
# -----------------------------
@router.delete("/delete/me_foro_comment/", response_model=ForoCommentDeleteResponse, dependencies=[Depends(auth_required)])
async def delete_my_foro_comment_route(
    delete_data: ForoCommentDeleteMeRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    token = credentials.credentials
    await delete_my_foro_comment(db, token, delete_data)
    return ForoCommentDeleteResponse(
        success=True,
        message="Comentario eliminado exitosamente"
    )




@router.get("/my-comments/", 
           response_model=ForoCommentListResponse,
           dependencies=[Depends(auth_required)])
async def get_my_comments_route(
    offset: int = Query(0, ge=0),
    limit: int = Query(6, ge=1, le=50),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene los comentarios del usuario autenticado"""
    token = credentials.credentials
    result = await get_my_comments(db, token, offset, limit)
    
    return ForoCommentListResponse(
        success=True,
        message="Mis comentarios obtenidos exitosamente",
        data=[ForoCommentListData.model_validate(item) for item in result["items"]],
        total=result["total"],
        offset=result["offset"],
        limit=result["limit"],
        has_more=result["has_more"]
    )

@router.get("/recent-comments/", 
           response_model=ForoCommentListResponse,
           dependencies=[Depends(auth_required)])
async def get_recent_comments_route(
    offset: int = Query(0, ge=0),
    limit: int = Query(6, ge=1, le=50),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene los comentarios más recientes"""
    token = credentials.credentials
    result = await get_recent_comments(db, token, offset, limit)
    
    return ForoCommentListResponse(
        success=True,
        message="Comentarios recientes obtenidos exitosamente",
        data=[ForoCommentListData.model_validate(item) for item in result["items"]],
        total=result["total"],
        offset=result["offset"],
        limit=result["limit"],
        has_more=result["has_more"]
    )



from app.services.foro.foro_reply_comment_service import (
    create_foro_reply_comment, update_my_foro_reply_comment, delete_my_foro_reply_comment, get_my_replies, get_recent_replies
)
from app.schemas.foro.foro_reply_comment_schema import (
    ForoReplyCommentCreateRequest, ForoReplyCommentCreateResponse, ForoReplyCommentCreateData,
    ForoReplyCommentUpdateMeRequest, ForoReplyCommentUpdateResponse, ForoReplyCommentUpdateData,
    ForoReplyCommentDeleteResponse, ForoReplyCommentDeleteMeRequest, ForoReplyCommentListData, ForoReplyCommentListResponse
)


 
# -----------------------------
# Create Reply
# -----------------------------
@router.post("/create_foro_reply_comment/", response_model=ForoReplyCommentCreateResponse, dependencies=[Depends(auth_required)])
async def create_foro_reply_comment_route(
    reply_data: ForoReplyCommentCreateRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    token = credentials.credentials
    reply = await create_foro_reply_comment(db, token, reply_data)
    return ForoReplyCommentCreateResponse(
        success=True,
        message="Respuesta creada exitosamente",
        data=ForoReplyCommentCreateData.model_validate(reply)
    )

# -----------------------------
# Update My Reply
# -----------------------------
@router.put("/update/me_foro_reply_comment/", response_model=ForoReplyCommentUpdateResponse, dependencies=[Depends(auth_required)])
async def update_my_foro_reply_comment_route(
    reply_data: ForoReplyCommentUpdateMeRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    token = credentials.credentials
    reply = await update_my_foro_reply_comment(db, token, reply_data)
    return ForoReplyCommentUpdateResponse(
        success=True,
        message="Respuesta actualizada exitosamente",
        data=ForoReplyCommentUpdateData.model_validate(reply)
    )

# -----------------------------
# Delete My Reply
# -----------------------------
@router.delete("/delete/me_foro_reply_comment/", response_model=ForoReplyCommentDeleteResponse, dependencies=[Depends(auth_required)])
async def delete_my_foro_reply_comment_route(
    delete_data: ForoReplyCommentDeleteMeRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    token = credentials.credentials
    await delete_my_foro_reply_comment(db, token, delete_data)
    return ForoReplyCommentDeleteResponse(
        success=True,
        message="Respuesta eliminada exitosamente"
    )





@router.get("/my-replies/", 
           response_model=ForoReplyCommentListResponse,
           dependencies=[Depends(auth_required)])
async def get_my_replies_route(
    offset: int = Query(0, ge=0),
    limit: int = Query(6, ge=1, le=50),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene las respuestas del usuario autenticado"""
    token = credentials.credentials
    result = await get_my_replies(db, token, offset, limit)
    
    return ForoReplyCommentListResponse(
        success=True,
        message="Mis respuestas obtenidas exitosamente",
        data=[ForoReplyCommentListData.model_validate(item) for item in result["items"]],
        total=result["total"],
        offset=result["offset"],
        limit=result["limit"],
        has_more=result["has_more"]
    )

@router.get("/recent-replies/", 
           response_model=ForoReplyCommentListResponse,
           dependencies=[Depends(auth_required)])
async def get_recent_replies_route(
    offset: int = Query(0, ge=0),
    limit: int = Query(6, ge=1, le=50),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene las respuestas más recientes"""
    token = credentials.credentials
    result = await get_recent_replies(db, token, offset, limit)
    
    return ForoReplyCommentListResponse(
        success=True,
        message="Respuestas recientes obtenidas exitosamente",
        data=[ForoReplyCommentListData.model_validate(item) for item in result["items"]],
        total=result["total"],
        offset=result["offset"],
        limit=result["limit"],
        has_more=result["has_more"]
    )