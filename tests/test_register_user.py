import pytest
from httpx import AsyncClient,ASGITransport
from app.main import app
from app.apis.deps import get_db
from tests.test_db import override_get_db, init_test_db, TestingSessionLocal
from app.models import Role, Status

# Sobrescribe get_db con la base de datos de prueba
app.dependency_overrides[get_db] = override_get_db

# Configura el test para usar la base de datos de prueba
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
            "email": "luissss@tes1t.com",
            "password": "Password123!!"
        })
        print(response.text)

    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "Luis" in data["success"]