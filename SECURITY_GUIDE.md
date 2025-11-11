# 🔒 Guía de Seguridad - OnlyCation APIs

## 📋 Tabla de Contenidos
1. [Sanitización de Inputs (XSS Protection)](#sanitización-de-inputs)
2. [Rate Limiting (Protección contra Brute Force)](#rate-limiting)
3. [SQL Injection Prevention](#sql-injection-prevention)
4. [Ejemplos de Implementación](#ejemplos)

---

## 🛡️ Sanitización de Inputs

### ¿Por qué es importante?
Los usuarios pueden enviar código malicioso como `<script>alert('XSS')</script>` en campos de texto, que luego se ejecuta en el navegador de otros usuarios.

### Cómo aplicarlo en Schemas de Pydantic

```python
from pydantic import BaseModel, field_validator
from app.cores.input_validator import sanitize_string_field, sanitize_html_field

class MiSchema(BaseModel):
    # Para campos que NO deben tener HTML (nombres, emails, etc.)
    nombre: str
    apellido: str
    
    # Para campos que SÍ pueden tener HTML básico (descripciones)
    descripcion: str
    
    # Sanitizar campos de texto plano
    _sanitize_nombre = field_validator('nombre')(sanitize_string_field)
    _sanitize_apellido = field_validator('apellido')(sanitize_string_field)
    
    # Sanitizar pero permitir HTML seguro
    _sanitize_desc = field_validator('descripcion')(sanitize_html_field)
```

### ✅ Schemas que DEBEN sanitizarse:

**Alta Prioridad:**
- ✅ `RegisterUserRequest` - first_name, last_name (YA IMPLEMENTADO)
- ⚠️ `ProfileUpdateRequest` - bio, nombre, etc.
- ⚠️ `TeacherProfileRequest` - descripción, experiencia
- ⚠️ `MessageRequest` - contenido de mensajes
- ⚠️ `CommentRequest` - comentarios de foros
- ⚠️ `ReviewRequest` - reseñas y valoraciones

**Media Prioridad:**
- `BookingRequest` - notas, comentarios
- `NotificationRequest` - mensaje
- `VideoRequest` - título, descripción

---

## 🚦 Rate Limiting

### ¿Por qué es importante?
Previene ataques de fuerza bruta (intentos masivos de login) y abuso del API.

### Cómo aplicarlo a endpoints

```python
from app.cores.rate_limiter import limiter
from fastapi import Request

@router.post("/login/")
@limiter.limit("5/minute")  # Máximo 5 intentos por minuto
async def login(request: Request, ...):
    ...

@router.post("/register/")
@limiter.limit("10/hour")  # Máximo 10 registros por hora
async def register(request: Request, ...):
    ...
```

### 🎯 Endpoints Críticos que DEBEN tener Rate Limiting:

**Alta Prioridad (Ya implementado en algunos):**
- ✅ `/api/auth/login/` - 5/minute (YA IMPLEMENTADO)
- ⚠️ `/api/auth/register/student/` - 10/hour
- ⚠️ `/api/auth/register/teacher/` - 10/hour
- ⚠️ `/api/auth/refresh-token/` - 20/minute
- ⚠️ `/api/auth/reset-password/` - 3/hour

**Media Prioridad:**
- `/api/bookings/create/` - 30/hour
- `/api/wallet/withdraw/` - 10/hour
- `/api/profile/update/` - 20/hour
- `/api/chat/send/` - 100/minute

**Baja Prioridad (rate limit global):**
- Todos los demás endpoints usan el límite global: 100/minute

---

## 💉 SQL Injection Prevention

### ¿Por qué es seguro?
SQLAlchemy con parámetros ya previene SQL injection, pero agregamos validación extra.

### Cómo usar el validador

```python
from pydantic import BaseModel, field_validator
from app.cores.input_validator import validate_no_sql_injection

class BusquedaSchema(BaseModel):
    query: str
    
    # Rechaza patrones sospechosos como "'; DROP TABLE --"
    _validate_query = field_validator('query')(validate_no_sql_injection)
```

**Usar en campos de búsqueda o filtros:**
- Búsquedas de profesores
- Filtros de cursos
- Queries de reportes

---

## 📝 Ejemplos Completos

### Ejemplo 1: Schema de Perfil con Sanitización

```python
from pydantic import BaseModel, field_validator
from app.cores.input_validator import sanitize_string_field, sanitize_html_field

class UpdateProfileRequest(BaseModel):
    first_name: str
    last_name: str
    bio: str  # Permite HTML básico
    ciudad: str
    
    # Sanitizar campos de texto plano
    _sanitize_first_name = field_validator('first_name')(sanitize_string_field)
    _sanitize_last_name = field_validator('last_name')(sanitize_string_field)
    _sanitize_ciudad = field_validator('ciudad')(sanitize_string_field)
    
    # Bio puede tener HTML básico como <strong>, <em>
    _sanitize_bio = field_validator('bio')(sanitize_html_field)
```

### Ejemplo 2: Endpoint con Rate Limiting

```python
from fastapi import APIRouter, Request
from app.cores.rate_limiter import limiter

router = APIRouter()

@router.post("/send-message/")
@limiter.limit("50/minute")  # 50 mensajes por minuto máximo
async def send_message(request: Request, message: MessageRequest, ...):
    # Tu lógica aquí
    pass
```

### Ejemplo 3: Validación Manual en Servicio

```python
from app.cores.input_validator import InputValidator

async def create_teacher_profile(data: dict):
    # Limpiar manualmente si es necesario
    clean_bio = InputValidator.clean_html(data.get('bio', ''))
    clean_name = InputValidator.clean_string(data.get('name', ''))
    
    # Validar longitud
    if not InputValidator.validate_length(clean_bio, max_len=5000):
        raise ValueError("Bio demasiado larga")
    
    # Continuar con la lógica...
```

---

## 🔍 Testing de Seguridad

### Probar XSS:
```bash
# Intentar registrar con HTML malicioso
curl -X POST "http://localhost:8000/api/auth/register/student/" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "<script>alert(\"XSS\")</script>",
    "last_name": "Test",
    "email": "test@test.com",
    "password": "Pass123!",
    "privacy_policy_accepted": true
  }'

# ✅ Resultado esperado: nombre limpio sin <script>
```

### Probar Rate Limiting:
```bash
# Intentar login 10 veces rápido
for i in {1..10}; do
  curl -X POST "http://localhost:8000/api/auth/login/"
done

# ✅ Resultado esperado: después de 5, retorna 429 Too Many Requests
```

---

## 📊 Checklist de Seguridad

### Antes de hacer Deploy:

- [ ] Todos los schemas de usuario tienen sanitización
- [ ] Endpoints de autenticación tienen rate limiting
- [ ] Endpoints de pagos tienen rate limiting estricto
- [ ] OWASP ZAP scan pasa sin errores
- [ ] Pytest pasa todos los tests
- [ ] Variables sensibles están en `.env` (no hardcodeadas)
- [ ] CORS configurado solo para dominios permitidos
- [ ] Headers de seguridad activos (SecurityHeadersMiddleware)

---

## 🚨 Reporte de Vulnerabilidades

Si encuentras una vulnerabilidad de seguridad, repórtala a: **security@onlycation.com**
