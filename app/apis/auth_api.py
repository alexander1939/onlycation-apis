
from fastapi import APIRouter, Depends, HTTPException
from app.schemas.auths.logout_sheme import DefaultResponse, LogoutRequest
from app.schemas.auths.refresh_token import RefreshTokenRequest
from app.services.auths.logout_service import logout_user
from app.services.auths.refresh_token_service import refresh_access_token
from app.services.auths.register_service import register_user
from app.schemas.auths.register_shema import RegisterUserRequest, RegisterUserResponse
from app.apis.deps import auth_required, get_db, public_access
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from app.schemas.auths.login_schema import LoginRequest, LoginResponse
from app.services.auths.login_service import login_user


from app.schemas.externals.email_schema import EmailSchema
from app.services.externals.email_service import send_email


router = APIRouter()


"""
Ruta para registrar un nuevo estudiante.
    - Crea un usuario con rol "student" y estado "active".
    - Retorna datos básicos del usuario registrado.
"""
@router.post("/register/student/", response_model=RegisterUserResponse, dependencies=[Depends(public_access)])
async def register_student_route(request: RegisterUserRequest, db: AsyncSession = Depends(get_db)):
    new_user = await register_user(request, "student", "active" ,db)
    return {
        "success": True,
        "message": "Successfully registered user.",
        "data": {
            "first_name":new_user.first_name,
            "last_name":new_user.last_name,
            "email":new_user.email

        }
    }

"""
Ruta para registrar un nuevo profesor.
    - Crea un usuario con rol "teacher" y estado "pending".
    - Retorna los datos del profesor registrado.
"""
@router.post("/register/teacher/",dependencies=[Depends(public_access)], response_model=RegisterUserResponse)
async def register_teacher_route(request: RegisterUserRequest, db: AsyncSession = Depends(get_db)):
    new_user = await register_user(request, "teacher", "pending", db)
    return {
        "success": True,
        "message": "Successfully registered user.",
        "data": {
            "first_name":new_user.first_name,
            "last_name":new_user.last_name,
            "email":new_user.email

        }
    }


"""
Ruta para iniciar sesión.
    - Verifica las credenciales y genera un token de acceso.
    - Devuelve el token, tipo de token y algunos datos del usuario.
"""
@router.post("/login/", response_model=LoginResponse, dependencies=[Depends(public_access)])
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    access_token, refresh_token, user = await login_user(db, request.email, request.password)# type: ignore
    return {
        "success": True,
        "message": "Login exitoso",
        "data": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role.name if user.role else None,
        }
    }

'''
Endpoint que cierra sesión invocando logout_user().
Elimina el refresh_token del usuario y confirma el logout.
'''
@router.post("/logout/", response_model=DefaultResponse, dependencies=[Depends(auth_required)])
async def logout(request: LogoutRequest, db: AsyncSession = Depends(get_db)):
    await logout_user(db, request.email)
    return {
        "success": True,
        "message": "Sesión cerrada correctamente",
    }


@router.post("/send")
async def send_email_api(email: EmailSchema):
    try:
        await send_email(email)
        return {"success": True, "message": "Correo enviado correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al enviar el correo: {str(e)}")



@router.post("/refresh-token/")
async def refresh_token(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    access_token, payload = await refresh_access_token(db, request.token)
    return {
        "success": True,
        "message": "Token renovado exitosamente",
        "data": {
            "access_token": access_token,
            "token_type": "bearer"
        }
    }

# @router.post("/send")
# async def send_email_api(email: EmailSchema):
#     try:
#         await send_email(email)
#         return {"success": True, "message": "Correo enviado correctamente"}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error al enviar el correo: {str(e)}")

from app.schemas.auths.password_reset_schema import PasswordResetRequest, PasswordResetVerify, PasswordResetCheckCode
from app.services.auths.password_reset_service import send_password_reset_email, verify_password_reset, check_verification_code_status

@router.post("/password-reset/request")
async def request_password_reset(
    request: PasswordResetRequest, 
    db: AsyncSession = Depends(get_db)
):
    return await send_password_reset_email(request, db)

@router.post("/password-reset/verify")
async def verify_password_reset_code(
    request: PasswordResetVerify, 
    db: AsyncSession = Depends(get_db)
):
    return await verify_password_reset(request, db)

@router.post("/password-reset/check-code")
async def check_verification_code(
    request: PasswordResetCheckCode, 
    db: AsyncSession = Depends(get_db)
):
    return await check_verification_code_status(request.code, db)