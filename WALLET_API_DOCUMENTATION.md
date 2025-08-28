# 🏦 API de Cartera Stripe Connect para Docentes

Esta API permite a los docentes gestionar sus pagos directamente a través de Stripe Connect, eliminando la necesidad de almacenamiento local de balances virtuales.

## 🚀 Funcionalidades Principales

### 1. **Gestión de Cartera Stripe**
- ✅ Crear cartera con cuenta Stripe Connect automática
- ✅ Consultar balance directamente desde Stripe
- ✅ Acceso al Stripe Express Dashboard
- ✅ Eliminar cartera (verificando balance en Stripe)

### 2. **Integración con Stripe Connect**
- ✅ Creación automática de cuenta Stripe Connect
- ✅ Enlaces de onboarding para configuración
- ✅ Verificar estado de la cuenta
- ✅ Dashboard link para gestión de pagos

### 3. **Gestión de Fondos**
- ✅ Balance y pagos manejados directamente en Stripe
- ✅ Retiros automáticos via Stripe Dashboard
- ✅ Historial de transacciones en Stripe

## 📋 Endpoints Disponibles

### **APIs Funcionales**

#### `POST /api/wallet/create/`
Crear una nueva cartera para el docente con cuenta Stripe Connect automática.

**Request Body:**
```json
{
  "country": "MX",
  "type": "express"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Cartera virtual creada. Completa la configuración en Stripe.",
  "data": {
    "wallet_id": 1,
    "stripe_account_id": "acct_1234567890",
    "stripe_status": "pending",
    "stripe_setup_url": "https://connect.stripe.com/setup/s/..."
  }
}
```

#### `GET /api/wallet/`
Obtener información completa de la cartera del docente autenticado.

#### `GET /api/wallet/balance/`
Obtener balance directamente desde Stripe Connect con enlace al dashboard.

**Response:**
```json
{
  "success": true,
  "message": "Balance obtenido exitosamente. Usa stripe_dashboard_url para ver detalles en Stripe.",
  "data": {
    "stripe_balance": 1500.50,
    "stripe_currency": "mxn",
    "pending_balance": 250.00,
    "account_status": "active",
    "stripe_dashboard_url": "https://connect.stripe.com/express/..."
  }
}
```

#### `DELETE /api/wallet/delete/`
Eliminar cartera (solo si no hay balance en Stripe).

## 🔐 Autenticación

Todos los endpoints requieren autenticación mediante token Bearer:

```
Authorization: Bearer <access_token>
```

## 📊 Estados de la Cuenta Stripe

- **`pending`**: Cuenta creada, pendiente de configuración
- **`pending_verification`**: Información enviada, pendiente de verificación
- **`active`**: Cuenta activa, puede recibir pagos

## 🔄 Flujo de Uso Típico

1. **Crear Cartera**: El docente crea su cartera (automáticamente crea cuenta Stripe Connect)
2. **Completar Onboarding**: Usar `stripe_setup_url` para completar configuración en Stripe
3. **Recibir Pagos**: Los fondos se reciben directamente en la cuenta Stripe
4. **Gestionar Fondos**: Usar el Stripe Dashboard para ver balance y configurar retiros automáticos

## ⚠️ Consideraciones Importantes

- Solo los usuarios con rol "teacher" pueden crear carteras
- Un docente solo puede tener una cartera
- La configuración bancaria se maneja completamente en Stripe
- Los balances y retiros se gestionan directamente en Stripe Dashboard
- No se puede eliminar una cartera con saldo en Stripe
- Todos los montos están en pesos mexicanos (MXN)

## 🛠️ Configuración Requerida

Asegúrate de tener configuradas las siguientes variables de entorno:

```env
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLIC_KEY=pk_test_...
```

## 📝 Notas Técnicas

- La API utiliza Decimal para precisión en cálculos monetarios
- Las transferencias a Stripe se procesan en centavos
- Todos los endpoints incluyen validación de datos y manejo de errores
- La integración es compatible con Stripe Connect Express accounts
