"""
Servicio de emails para notificaciones de reservas con información detallada
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi_mail import FastMail, MessageSchema
from datetime import datetime
from typing import Optional
import logging

from app.external.email_config import conf
from app.models.users.user import User

logger = logging.getLogger(__name__)


async def send_booking_confirmation_email(
    db: AsyncSession,
    student_id: int,
    booking_details: dict
) -> bool:
    """
    Enviar email de confirmación de reserva al estudiante con detalles específicos
    """
    try:
        # Obtener datos del estudiante
        user_result = await db.execute(
            select(User).where(User.id == student_id)
        )
        user = user_result.scalar_one()
        
        subject = "¡Reserva confirmada! - OnlyCation"
        
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #4CAF50;">¡Tu reserva ha sido confirmada!</h2>
                
                <p>Hola <strong>{user.first_name} {user.last_name}</strong>,</p>
                
                <p>Tu reserva ha sido confirmada exitosamente. Aquí están los detalles:</p>
                
                <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="color: #333; margin-top: 0;">Detalles de la Reserva</h3>
                    <p><strong>Fecha y Hora:</strong> {booking_details.get('start_date', 'Fecha de inicio')} - {booking_details.get('end_date', 'Fecha de fin')}</p>
                    <p><strong>Docente:</strong> {booking_details.get('teacher_name', 'Por confirmar')}</p>
                </div>
                
                <p>Te enviaremos más detalles sobre el enlace de la clase próximamente.</p>
                
                <p style="margin-top: 30px;">
                    Saludos,<br>
                    <strong>El equipo de OnlyCation</strong>
                </p>
            </div>
        </body>
        </html>
        """
        
        message = MessageSchema(
            subject=subject,
            recipients=[user.email],
            body=body,
            subtype="html"
        )
        
        fm = FastMail(conf)
        await fm.send_message(message)
        
        logger.info(f"✅ Email de confirmación enviado a {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error enviando email de confirmación: {str(e)}")
        return False


async def send_payment_confirmation_email(
    db: AsyncSession,
    student_id: int,
    payment_details: dict
) -> bool:
    """
    Enviar email de confirmación de pago al estudiante
    """
    try:
        # Obtener datos del estudiante
        user_result = await db.execute(
            select(User).where(User.id == student_id)
        )
        user = user_result.scalar_one()
        
        # Convertir amount de centavos a pesos
        amount_in_pesos = payment_details.get('amount', 0) / 100
        
        subject = "Pago confirmado - OnlyCation"
        
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #4CAF50;">¡Pago procesado exitosamente!</h2>
                
                <p>Hola <strong>{user.first_name} {user.last_name}</strong>,</p>
                
                <p>Tu pago ha sido procesado correctamente. Aquí están los detalles:</p>
                
                <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="color: #333; margin-top: 0;">Detalles del Pago</h3>
                    <p><strong>Monto:</strong> ${amount_in_pesos:.2f} MXN</p>
                    <p><strong>Estado:</strong> Confirmado</p>
                    <p><strong>Fecha:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                </div>
                
                <p>Tu reserva está confirmada y lista. ¡Nos vemos en clase!</p>
                
                <p style="margin-top: 30px;">
                    Saludos,<br>
                    <strong>El equipo de OnlyCation</strong>
                </p>
            </div>
        </body>
        </html>
        """
        
        message = MessageSchema(
            subject=subject,
            recipients=[user.email],
            body=body,
            subtype="html"
        )
        
        fm = FastMail(conf)
        await fm.send_message(message)
        
        logger.info(f"✅ Email de pago enviado a {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error enviando email de pago: {str(e)}")
        return False


async def send_new_booking_email_to_teacher(
    db: AsyncSession,
    teacher_id: int,
    booking_details: dict
) -> bool:
    """
    Enviar email al docente sobre nueva reserva
    """
    try:
        # Obtener datos del docente
        user_result = await db.execute(
            select(User).where(User.id == teacher_id)
        )
        user = user_result.scalar_one()
        
        subject = "Nueva reserva recibida - OnlyCation"
        
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2196F3;">¡Tienes una nueva reserva!</h2>
                
                <p>Hola <strong>{user.first_name} {user.last_name}</strong>,</p>
                
                <p>Has recibido una nueva reserva. Aquí están los detalles:</p>
                
                <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="color: #333; margin-top: 0;">Detalles de la Reserva</h3>
                    <p><strong>Estudiante:</strong> {booking_details.get('student_name', 'Estudiante')}</p>
                    <p><strong>Fecha y Hora:</strong> {booking_details.get('start_date', 'Fecha de inicio')} - {booking_details.get('end_date', 'Fecha de fin')}</p>
                </div>
                
                <p>Revisa tu panel de docente para más detalles y preparar la clase.</p>
                
                <p style="margin-top: 30px;">
                    Saludos,<br>
                    <strong>El equipo de OnlyCation</strong>
                </p>
            </div>
        </body>
        </html>
        """
        
        message = MessageSchema(
            subject=subject,
            recipients=[user.email],
            body=body,
            subtype="html"
        )
        
        fm = FastMail(conf)
        await fm.send_message(message)
        
        logger.info(f"✅ Email de nueva reserva enviado a {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error enviando email de nueva reserva: {str(e)}")
        return False


async def send_reschedule_request_email(
    db: AsyncSession,
    student_id: int,
    reschedule_details: dict
) -> bool:
    """
    Enviar email al estudiante sobre solicitud de reagendado
    """
    try:
        # Obtener datos del estudiante
        user_result = await db.execute(
            select(User).where(User.id == student_id)
        )
        user = user_result.scalar_one()
        
        subject = "Solicitud de reagendado - OnlyCation"
        
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #FF9800;">Solicitud de reagendado recibida</h2>
                
                <p>Hola <strong>{user.first_name} {user.last_name}</strong>,</p>
                
                <p>Has recibido una solicitud para reagendar una de tus clases:</p>
                
                <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="color: #333; margin-top: 0;">Detalles de la Solicitud</h3>
                    <p><strong>Docente:</strong> {reschedule_details.get('teacher_name', 'Docente')}</p>
                    <p><strong>Fecha actual:</strong> {reschedule_details.get('current_start_date', 'Fecha de inicio actual')} - {reschedule_details.get('current_end_date', 'Fecha de fin actual')}</p>
                    <p><strong>Nueva fecha propuesta:</strong> {reschedule_details.get('new_start_date', 'Nueva fecha de inicio')} - {reschedule_details.get('new_end_date', 'Nueva fecha de fin')}</p>
                    {f"<p><strong>Motivo:</strong> {reschedule_details.get('reason', '')}</p>" if reschedule_details.get('reason') else ""}
                </div>
                
                <p>Por favor, revisa tu panel de estudiante para aprobar o rechazar esta solicitud.</p>
                
                <p style="margin-top: 30px;">
                    Saludos,<br>
                    <strong>El equipo de OnlyCation</strong>
                </p>
            </div>
        </body>
        </html>
        """
        
        message = MessageSchema(
            subject=subject,
            recipients=[user.email],
            body=body,
            subtype="html"
        )
        
        fm = FastMail(conf)
        await fm.send_message(message)
        
        logger.info(f"✅ Email de solicitud de reagendado enviado a {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error enviando email de solicitud de reagendado: {str(e)}")
        return False


async def send_reschedule_response_email(
    db: AsyncSession,
    teacher_id: int,
    response_details: dict
) -> bool:
    """
    Enviar email al docente sobre respuesta de reagendado
    """
    try:
        # Obtener datos del docente
        user_result = await db.execute(
            select(User).where(User.id == teacher_id)
        )
        user = user_result.scalar_one()
        
        approved = response_details.get('approved', False)
        action = "aprobada" if approved else "rechazada"
        color = "#4CAF50" if approved else "#F44336"
        
        subject = f"Solicitud de reagendado {action} - OnlyCation"
        
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: {color};">Solicitud de reagendado {action}</h2>
                
                <p>Hola <strong>{user.first_name} {user.last_name}</strong>,</p>
                
                <p>Tu solicitud de reagendado ha sido <strong>{action}</strong>.</p>
                
                <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="color: #333; margin-top: 0;">Detalles de la Respuesta</h3>
                    <p><strong>Estudiante:</strong> {response_details.get('student_name', 'Estudiante')}</p>
                    <p><strong>Estado:</strong> {action.capitalize()}</p>
                    {f"<p><strong>Mensaje del estudiante:</strong> {response_details.get('response_message', '')}</p>" if response_details.get('response_message') else ""}
                </div>
                
                {"<p>¡Excelente! La clase ha sido reagendada al nuevo horario.</p>" if approved else "<p>La clase se mantendrá en el horario original.</p>"}
                
                <p style="margin-top: 30px;">
                    Saludos,<br>
                    <strong>El equipo de OnlyCation</strong>
                </p>
            </div>
        </body>
        </html>
        """
        
        message = MessageSchema(
            subject=subject,
            recipients=[user.email],
            body=body,
            subtype="html"
        )
        
        fm = FastMail(conf)
        await fm.send_message(message)
        
        logger.info(f"✅ Email de respuesta de reagendado enviado a {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error enviando email de respuesta de reagendado: {str(e)}")
        return False


async def send_booking_rescheduled_email(
    db: AsyncSession,
    user_id: int,
    reschedule_details: dict
) -> bool:
    """
    Enviar email cuando una reserva ha sido reagendada exitosamente
    """
    try:
        # Obtener datos del usuario
        user_result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one()
        
        subject = "Reserva reagendada exitosamente - OnlyCation"
        
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #4CAF50;">¡Reserva reagendada exitosamente!</h2>
                
                <p>Hola <strong>{user.first_name} {user.last_name}</strong>,</p>
                
                <p>Tu reserva ha sido reagendada exitosamente.</p>
                
                <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="color: #333; margin-top: 0;">Información del Reagendado</h3>
                    <p><strong>Fecha anterior:</strong> {reschedule_details.get('old_start_date', 'Fecha de inicio anterior')} - {reschedule_details.get('old_end_date', 'Fecha de fin anterior')}</p>
                    <p><strong>Nueva fecha:</strong> {reschedule_details.get('new_start_date', 'Nueva fecha de inicio')} - {reschedule_details.get('new_end_date', 'Nueva fecha de fin')}</p>
                    <p><strong>Estado:</strong> Confirmado</p>
                </div>
                
                <p>Revisa tu panel para ver todos los detalles actualizados de tu clase.</p>
                
                <p style="margin-top: 30px;">
                    Saludos,<br>
                    <strong>El equipo de OnlyCation</strong>
                </p>
            </div>
        </body>
        </html>
        """
        
        message = MessageSchema(
            subject=subject,
            recipients=[user.email],
            body=body,
            subtype="html"
        )
        
        fm = FastMail(conf)
        await fm.send_message(message)
        
        logger.info(f"✅ Email de reagendado exitoso enviado a {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error enviando email de reagendado exitoso: {str(e)}")
        return False
