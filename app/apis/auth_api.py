
from fastapi import APIRouter, Depends
from app.services.auths.register_service import register_user
from app.schemas.auths.register_shema import RegisterUserRequest, RegisterUserResponse
from app.apis.deps import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from app.schemas.auths.login_schema import LoginRequest, LoginResponse
from app.services.auths.login_service import login_user


from fastapi import APIRouter, HTTPException
from app.schemas.externals.email_schema import EmailSchema
from app.services.externals.email_service import send_email

router = APIRouter()


@router.post("/register/student/", response_model=RegisterUserResponse)
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

@router.post("/register/teacher/")
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

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    token, user = await login_user(db, request.email, request.password)
    return {
        "success": True,
        "message": "Login exitoso",
        "data": {
            "access_token": token,
            "token_type": "bearer",
            "email": user.email,
            "first_name": user.first_name,
            "status": user.statuses.name, 
        }
    }



@router.post("/send")
async def send_email_api(email: EmailSchema):
    try:
        await send_email(email)
        return {"success": True, "message": "Correo enviado correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al enviar el correo: {str(e)}")
