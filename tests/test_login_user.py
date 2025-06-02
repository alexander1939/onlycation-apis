import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.apis.deps import get_db
from tests.test_db import override_get_db, init_test_db, TestingSessionLocal
from app.models import Role, Status, User
from app.cores.security import get_password_hash


app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module", autouse=True)
async def prepare_db():
    await init_test_db()
    async with TestingSessionLocal() as session:
        # Crear roles y estatus
        student_role = Role(name="student")
        active_status = Status(name="active")
        session.add_all([
            student_role,
            Role(name="teacher"),
            active_status,
            Status(name="inactive"),
        ])
        await session.commit()

        # Crear usuario de prueba
        hashed_pw = get_password_hash("Password123!!")
        user = User(
            first_name="Luis",
            last_name="Gonzalez",
            email="luis@tes1t.com",
            password=hashed_pw,
            role_id=student_role.id,
            status_id=active_status.id,
            privacy_policy_accepted=True,
        )
        session.add(user)
        await session.commit()

@pytest.mark.asyncio
async def test_login_user():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/auth/login/", json={
            "email": "luis@tes1t.com",
            "password": "Password123!!"
        })
        print(response.text)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["first_name"] == "Luis"
    assert data["data"]["last_name"] == "Gonzalez"

@pytest.mark.asyncio
async def test_login_user_detail_password():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/auth/login/", json={
            "email": "luis@tes1t.com",
            "password": "Password12!!"
        })
        print(response.text)

    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Correo o contraseña incorrectos"


@pytest.mark.asyncio
async def test_login_user_detail_email():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/auth/login/", json={
            "email": "luis@gmail.com",
            "password": "Password123!!"
        })
        print(response.text)

    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Correo o contraseña incorrectos"

@pytest.mark.asyncio
async def test_login_user_fields_email():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/auth/login/", json={
            "password": "Password123!!"
        })
        print(response.text)

    assert response.status_code == 422 
    data = response.json()
    assert any(error["loc"] == ["body", "email"] for error in data["detail"])

@pytest.mark.asyncio
async def test_login_user_fields_email():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/auth/login/", json={
            "email": "luis@gmail.com"
        })
        print(response.text)

    assert response.status_code == 422 
    data = response.json()
    assert any(error["loc"] == ["body", "password"] for error in data["detail"])