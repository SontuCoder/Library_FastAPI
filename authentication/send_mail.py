import random
import aiosmtplib
from email.message import EmailMessage
import os


async def send_mail_fast(to: str, otp:str):
    msg = EmailMessage()
    msg["From"] = os.getenv("EMAIL_FROM")
    msg["To"] = to
    msg["Subject"] = "Login Otp"
    msg.set_content(f"Your Login mail is {otp}")

    await aiosmtplib.send(
        message=msg,
        hostname=os.getenv("EMAIL_HOST"),
        port=int(os.getenv("EMAIL_PORT")),
        username=os.getenv("EMAIL_FROM"),
        password=os.getenv("EMAIL_PASS"),
        start_tls=True
    )



def generate_otp() -> str:
    return str(random.randint(100000, 999999))
