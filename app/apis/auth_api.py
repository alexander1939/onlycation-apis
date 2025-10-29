from app.models.users.user import User

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from app.schemas.auths.logout_sheme import DefaultResponse, LogoutRequest
from app.schemas.auths.refresh_token import RefreshTokenRequest
from app.services.auths.logout_service import logout_user
from app.services.auths.refresh_token_service import refresh_access_token
from app.services.auths.register_service import register_user
from app.schemas.auths.register_shema import RegisterUserRequest, RegisterUserResponse
from app.apis.deps import auth_required, get_db, public_access
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from urllib.parse import urlencode, quote
from sqlalchemy.orm import Session
from app.schemas.auths.login_schema import LoginRequest, LoginResponse
from app.configs.settings import settings
from app.services.auths.login_service import login_user
from app.services.auths.linkedin_auth_service import linkedin_auth
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


@router.get("/linkedin/login", dependencies=[Depends(public_access)])
async def linkedin_login(code: str | None = None, state: str | None = None, client_redirect: str | None = None, db: AsyncSession = Depends(get_db)):
    """
    LinkedIn OAuth2 entry point.
    - If no 'code' is provided, returns the authorization URL to start OAuth.
    - If 'code' is provided (LinkedIn callback), exchanges it for tokens and logs the user in.
    """
    try:
        if not settings.LINKEDIN_CLIENT_ID or not settings.LINKEDIN_CLIENT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="LinkedIn OAuth is not properly configured"
            )

        # If LinkedIn redirected back with a code, complete the OAuth flow here
        if code:
            tokens = await linkedin_auth.get_access_token(code)
            access_token = tokens.get("access_token")
            if not access_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get access token from LinkedIn"
                )

            user_info = await linkedin_auth.get_user_info(access_token)
            # Handle registration via state when provided
            if state and state.startswith("register:"):
                role_key = state.split(":", 1)[1]
                if role_key not in ("student", "teacher"):
                    raise HTTPException(status_code=400, detail="Invalid registration role")
                status_name = "active" if role_key == "student" else "pending"
                user = await linkedin_auth.create_user_with_role(db, user_info, role_name=role_key, status_name=status_name)
            else:
                # Pure login flow: only allow if user already exists
                result = await db.execute(select(User).where(User.email == user_info["email"]))
                user = result.scalar_one_or_none()
                if not user:
                    # Provide registration links
                    base = str(settings.LINKEDIN_REDIRECT_URI)
                    # The login endpoint returns authorization links when called without code
                    student_register_link = f"/api/auth/linkedin/register/student"
                    teacher_register_link = f"/api/auth/linkedin/register/teacher"
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "message": "User not found. Please register with LinkedIn.",
                            "register_student": student_register_link,
                            "register_teacher": teacher_register_link,
                        },
                    )

            # Reuse existing login service for token generation (OAuth mode)
            access_token, refresh_token, _ = await login_user(db=db, email=user.email, password=None, is_oauth=True)  # type: ignore

            # If a client_redirect is provided (or encoded in state), redirect back to app with tokens
            redirect_target = client_redirect
            # Try to extract redirect from state if not provided directly
            if not redirect_target and state and "redirect=" in state:
                try:
                    redirect_target = state.split("redirect=", 1)[1]
                except Exception:
                    redirect_target = None

            if redirect_target:
                params = urlencode({
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_type": "bearer",
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role.name if user.role else "",
                })
                return RedirectResponse(url=f"{redirect_target}?{params}")

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

        # Otherwise return the authorization URL to start the flow
        # Compose state to carry client_redirect if provided
        composed_state = state
        if client_redirect:
            composed_state = f"{state or 'login'}|redirect={client_redirect}"
        url_obj = linkedin_auth.get_authorization_url(state=composed_state)
        return {"authorization_url": url_obj.get("authorization_url")}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error handling LinkedIn OAuth: {str(e)}"
        )


@router.get("/linkedin/register/student", dependencies=[Depends(public_access)])
async def linkedin_register_student():
    try:
        url_obj = linkedin_auth.get_authorization_url(state="register:student")
        return {"authorization_url": url_obj.get("authorization_url")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating LinkedIn student register URL: {str(e)}")


@router.get("/linkedin/register/teacher", dependencies=[Depends(public_access)])
async def linkedin_register_teacher():
    try:
        url_obj = linkedin_auth.get_authorization_url(state="register:teacher")
        return {"authorization_url": url_obj.get("authorization_url")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating LinkedIn teacher register URL: {str(e)}")


@router.get("/linkedin/callback", dependencies=[Depends(public_access)])
async def linkedin_callback(code: str, state: str | None = None, client_redirect: str | None = None, db: AsyncSession = Depends(get_db)):
    
    try:
        if not code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authorization code is required"
            )
            
        # Exchange code for access token
        tokens = await linkedin_auth.get_access_token(code)
        access_token = tokens.get("access_token")

        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get access token from LinkedIn"
            )

        # Get user info from LinkedIn
        user_info = await linkedin_auth.get_user_info(access_token)

        if state and state.startswith("register:"):
            role_key = state.split(":", 1)[1]
            if role_key not in ("student", "teacher"):
                raise HTTPException(status_code=400, detail="Invalid registration role")
            status_name = "active" if role_key == "student" else "pending"
            user = await linkedin_auth.create_user_with_role(db, user_info, role_name=role_key, status_name=status_name)
        else:
            result = await db.execute(select(User).where(User.email == user_info["email"]))
            user = result.scalar_one_or_none()
            if not user:
                # Provide registration links
                student_register_link = f"/api/auth/linkedin/register/student"
                teacher_register_link = f"/api/auth/linkedin/register/teacher"
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "User not found. Please register with LinkedIn.",
                        "register_student": student_register_link,
                        "register_teacher": teacher_register_link,
                    },
                )

        # Generate JWT tokens (login_user returns tuple: access_token, refresh_token, user)
        access_token, refresh_token, _ = await login_user(
            db=db,
            email=user.email,
            password=None,  # OAuth users don't need password
            is_oauth=True
        )

        redirect_target = client_redirect
        if not redirect_target and state:
            if "redirect=" in state:
                try:
                    redirect_target = state.split("redirect=", 1)[1]
                except Exception:
                    redirect_target = None
            elif "|redir:" in state:
                try:
                    _, redirect_target = state.split("|redir:", 1)
                except Exception:
                    redirect_target = None

        # Default deep link for mobile apps if not explicitly provided
        if not redirect_target:
            redirect_target = "onlycation://auth"

        if redirect_target:
            return RedirectResponse(
                url=f"{redirect_target}?token={access_token}",
                status_code=307
            )

        # Build response matching app.schemas.auths.login_schema.LoginResponse (web fallback)
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
                "role": user.role.name if user.role else "",
            }
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error in LinkedIn callback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to authenticate with LinkedIn: {str(e)}"
        )


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