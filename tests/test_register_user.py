import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.apis.deps import get_db
from tests.test_db import override_get_db, init_test_db, TestingSessionLocal
from app.models import Role, Status

# Sobrescribe get_db con la base de datos de prueba
app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module", autouse=True)
async def prepare_db():
    await init_test_db()
    async with TestingSessionLocal() as session:
        session.add_all([
            Role(name="student"),
            Role(name="teacher"),
            Status(name="active"),
            Status(name="inactive"),
        ])
        await session.commit()

@pytest.mark.asyncio
async def test_register_student():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/auth/register/student/", json={
            "first_name": "Luis",
            "last_name": "Cruz",
            "email": "luis@tes12t.com",
            "password": "Password123!!",
            "privacy_policy_accepted": True,
        })
        print(response.text)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["first_name"] == "Luis"

# 1. Campos faltantes (sin email)
@pytest.mark.asyncio
async def test_missing_fields():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/auth/register/student/", json={
            "first_name": "Luis",
            "last_name": "Cruz",
            "password": "Password123!!",
            "privacy_policy_accepted": True,
        })
        print("FALTAN CAMPOS:", response.text)

    assert response.status_code == 422 
    data = response.json()
    assert any(error["loc"] == ["body", "email"] for error in data["detail"])

@pytest.mark.asyncio
async def test_duplicate_email():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/auth/register/student/", json={
            "first_name": "Luis",
            "last_name": "Cruz",
            "email": "luis@tes1t.com",  # Ya se usó
            "password": "Password123!!",
            "privacy_policy_accepted": True,
        })
        print("CORREO DUPLICADO:", response.text)

    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "Error registering email, please try another email."

# 2. Contraseña muy corta
@pytest.mark.asyncio
async def test_password_too_short():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/auth/register/student/", json={
            "first_name": "Ana",
            "last_name": "García",
            "email": "ana@example.com",
            "password": "Ab1!",  # Solo 4 caracteres
            "privacy_policy_accepted": True,
        })
        print("PASSWORD CORTA:", response.text)

    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "Password must be at least 8 characters long"

# 3. Contraseña sin carácter especial
@pytest.mark.asyncio
async def test_password_missing_special_character():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/auth/register/student/", json={
            "first_name": "Juan",
            "last_name": "López",
            "email": "juan@example.com",
            "password": "Password123",  # No tiene símbolo especial
            "privacy_policy_accepted": True,
        })
        print("PASSWORD SIN ESPECIAL:", response.text)

    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "Password must contain at least one special character"