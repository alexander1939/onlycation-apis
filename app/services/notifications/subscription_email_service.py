from datetime import datetime
from app.services.externals.email_service import send_email
from app.schemas.externals.email_schema import EmailSchema
from app.models.users import User
from app.models.subscriptions import Plan

async def send_subscription_confirmation_email(user: User, plan: Plan):
    """Envía email de confirmación de suscripción"""
    try:
        # Crear template HTML para el email
        email_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #4CAF50; color: white; padding: 20px; text-align: center;">
                <h1>¡Suscripción Confirmada! 🎉</h1>
            </div>
            
            <div style="padding: 20px;">
                <h2>Hola {user.first_name} {user.last_name},</h2>
                
                <p>¡Excelente noticia! Tu suscripción al <strong>{plan.name}</strong> ha sido confirmada exitosamente.</p>
                
                <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3>Detalles de tu suscripción:</h3>
                    <ul>
                        <li><strong>Plan:</strong> {plan.name}</li>
                        <li><strong>Precio:</strong> ${plan.price} MXN</li>
                        <li><strong>Estado:</strong> Activa</li>
                        <li><strong>Fecha de inicio:</strong> {datetime.utcnow().strftime('%d/%m/%Y')}</li>
                    </ul>
                </div>
                
                <p>Ahora puedes disfrutar de todos los beneficios de tu plan premium:</p>
                <ul>
                    <li>✅ Acceso completo a la plataforma</li>
                    <li>✅ Funciones avanzadas</li>
                    <li>✅ Soporte prioritario</li>
                </ul>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="#" style="background-color: #4CAF50; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px;">
                        Acceder a mi cuenta
                    </a>
                </div>
                
                <p>Si tienes alguna pregunta, no dudes en contactarnos.</p>
                
                <p>¡Gracias por confiar en OnlyCation!</p>
                
                <hr style="margin: 30px 0;">
                <p style="color: #666; font-size: 12px;">
                    Este es un email automático, por favor no respondas a este mensaje.
                </p>
            </div>
        </body>
        </html>
        """
        
        email_data = EmailSchema(
            email=user.email,
            subject=f"✅ Suscripción confirmada - {plan.name}",
            body=email_body
        )
        
        await send_email(email_data)
        
    except Exception as e:
        print(f"❌ Error enviando email de suscripción: {str(e)}")

async def send_subscription_welcome_email(user: User):
    """Envía email de bienvenida para nuevos usuarios"""
    try:
        email_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #2196F3; color: white; padding: 20px; text-align: center;">
                <h1>¡Bienvenido a OnlyCation! 👋</h1>
            </div>
            
            <div style="padding: 20px;">
                <h2>Hola {user.first_name},</h2>
                
                <p>¡Nos alegra tenerte en nuestra plataforma educativa!</p>
                
                <p>OnlyCation es tu espacio para conectar con los mejores profesores y expandir tus conocimientos.</p>
                
                <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3>¿Qué puedes hacer ahora?</h3>
                    <ul>
                        <li>🔍 Explorar profesores disponibles</li>
                        <li>📚 Reservar clases personalizadas</li>
                        <li>💬 Comunicarte directamente con tutores</li>
                        <li>📊 Seguir tu progreso de aprendizaje</li>
                    </ul>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="#" style="background-color: #2196F3; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px;">
                        Comenzar ahora
                    </a>
                </div>
                
                <p>¡Esperamos que tengas una excelente experiencia de aprendizaje!</p>
                
                <p>El equipo de OnlyCation</p>
            </div>
        </body>
        </html>
        """
        
        email_data = EmailSchema(
            email=user.email,
            subject="¡Bienvenido a OnlyCation! 🎓",
            body=email_body
        )
        
        await send_email(email_data)
        
    except Exception as e:
        print(f"❌ Error enviando email de bienvenida: {str(e)}")
