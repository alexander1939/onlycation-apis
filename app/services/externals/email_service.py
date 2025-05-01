from fastapi_mail import FastMail, MessageSchema
from app.external.email_config import conf
from app.schemas.externals.email_schema import EmailSchema

async def send_email(email_data: EmailSchema):
    message = MessageSchema(
        subject=email_data.subject,
        recipients=[email_data.email],
        body=email_data.body,
        subtype="html"
    )

    fm = FastMail(conf)
    await fm.send_message(message)
