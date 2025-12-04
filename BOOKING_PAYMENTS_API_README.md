# Booking Payments APIs (Reserva y Pagos)

Este documento describe las APIs involucradas en el flujo de pago de una reserva (crear sesión de pago y confirmar/verificar el pago) usando Stripe Checkout con Stripe Connect.

Flujo resumido
1) Crear sesión de pago (Checkout) → regresa `url` y `session_id` para pagar en Stripe.
2) Verificar pago (callback del frontend) → crea Booking, PaymentBooking, Confirmation, notifica y devuelve IDs.

Base URL
- Local: http://localhost:8000

Autenticación y Rate Limit
- Ambas rutas requieren autenticación (Bearer token).
- Límite global: 100 req/min por IP (configurable en `app/cores/rate_limiter.py`).

Rutas relevantes
- Código API: `app/apis/booking_api.py`
- Sesión de pago: `app/services/bookings/stripe_session_service.py`
- Verificación y creación de registros: `app/services/bookings/payment_verification_service.py`

---

## 1) Crear sesión de pago
POST /api/bookings/crear-booking/

Crea una Stripe Checkout Session para pagar una o varias horas corridas dentro de una disponibilidad del docente.

Headers
- Authorization: Bearer <JWT>
- Content-Type: application/json

Body (JSON) — `BookingRequest` (`app/schemas/bookings/booking_shema.py`)
```json
{
  "availability_id": 123,
  "price_id": 1,
  "start_time": "2025-12-01T09:00:00",
  "end_time": "2025-12-01T12:00:00",
  "total_hours": 3
}
```
Notas del request
- `availability_id`: ID de disponibilidad del docente.
- `price_id`: presente en el esquema, pero el sistema obtiene el precio real por `user_id` y `preference_id` de la disponibilidad (no confía en el enviado).
- `start_time` y `end_time`: ISO 8601. Deben ser horas exactas HH:00 y múltiplos de 1h.
- `total_hours`: informativo; el servicio recalcula con `end_time - start_time`.

Validaciones clave (en `create_booking_payment_session`)
- Horarios en futuro (no se permite reservar en el pasado).
- Anticipación mínima: 1 hora antes del inicio.
- Horas exactas: HH:00 y múltiplos de 1 hora.
- Rango dentro de la disponibilidad del docente (día correcto y entre `start_time`/`end_time` de la disponibilidad).
- Sin traslapes con otras reservas (excluye canceladas).
- El mismo usuario no puede tener otra reserva que traslape.

Cálculo de precio
- Modelo de precio del docente: `Price.selected_prices` (primera hora) y `Price.extra_hour_price` (hora extra).
- Fórmula: `total_price = base + (total_hours - 1) * extra_hour_price`.
- El precio de “hora extra” solo aplica dentro de un bloque corrido (ej. 09:00–12:00). Si haces otra reserva separada (ej. 16:00–18:00), es otro cálculo independiente.

Stripe Connect
- El sistema calcula comisión de la plataforma (`commission_rate`) y usa `application_fee_amount` + `transfer_data.destination` para enviar al docente (Connect).
- Metadatos de la sesión incluyen: `user_id`, `price_id`, `availability_id`, `start_time`, `end_time`, `total_hours`, `teacher_id`, `teacher_email`, `commission_rate`, `commission_amount`, `teacher_amount`, `teacher_stripe_account_id`.

Respuesta (200)
```json
{
  "success": true,
  "message": "Sesión de pago creada exitosamente",
  "data": {
    "url": "https://checkout.stripe.com/c/pay/cs_test_...",
    "session_id": "cs_test_...",
    "price": 650.0
  }
}
```

Ejemplo curl
```bash
curl -X POST "http://localhost:8000/api/bookings/crear-booking/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "availability_id": 123,
    "price_id": 1,
    "start_time": "2025-12-01T09:00:00",
    "end_time": "2025-12-01T12:00:00",
    "total_hours": 3
  }'
```

Errores comunes
- 400: horario fuera de disponibilidad, traslape, duración no múltiplo de 1h, reserva en el pasado o sin anticipación mínima.
- 404: disponibilidad o precio no encontrado.
- 409: conflicto por traslape.
- 500: error interno o con Stripe.

---

## 2) Verificar pago y crear registros
GET /api/bookings/verificar-booking/{session_id}

Valida el estado de pago en Stripe y, si está pagado, crea los registros de negocio.

Headers
- Authorization: Bearer <JWT>

Path params
- `session_id`: ID de la Stripe Checkout Session devuelta previamente.

Proceso interno (en `verify_booking_payment_and_create_records`)
- Obtiene la sesión en Stripe y valida:
  - El `user_id` en metadata coincide con el usuario autenticado.
  - `payment_status == "paid"`.
  - Idempotencia: no se ha procesado antes `payment_intent_id`.
- Crea `Booking` con `start_time`, `end_time`, `availability_id` y `status` activo.
- Genera `class_link` seguro (`generate_secure_room_link`).
- Crea `PaymentBooking` con montos (centavos), comisión, fecha de transferencia (`end_time + 15 días`) y `stripe_payment_intent_id`.
- Crea `Confirmation` (teacher_id, student_id, payment_booking_id).
- Envía notificaciones y correos (estudiante y docente).
- Commit y respuesta final.

Respuesta (200)
```json
{
  "success": true,
  "message": "Booking payment verified successfully",
  "payment_status": "completed",
  "data": {
    "booking_id": 456,
    "payment_booking_id": 789,
    "confirmation_id": 321
  }
}
```

Ejemplo curl
```bash
curl -X GET "http://localhost:8000/api/bookings/verificar-booking/$SESSION_ID" \
  -H "Authorization: Bearer $TOKEN"
```

Errores comunes
- 400: pago no completado, sesión inválida, o timestamps inválidos.
- 403: el `user_id` de la sesión no coincide con el usuario autenticado.
- 409: pago ya procesado.
- 404: recursos relacionados no encontrados.
- 500: error interno.

---

Notas y buenas prácticas
- Asegura que el frontend invoque la verificación tras el `success_url` de Stripe (en la URL viene `{CHECKOUT_SESSION_ID}`).
- Maneja las respuestas 4xx/5xx para mostrar mensajes claros al usuario.
- Para ambientes productivos usa almacenamiento de rate limit (Redis) en lugar de memoria.
- El precio mostrado por la API se calcula en backend; no confíes en precios enviados por el cliente.
