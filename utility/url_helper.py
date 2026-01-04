import secrets
from db_connection.redis_config import redis_client

def generate_otp_context_token(email:str):
    token = secrets.token_urlsafe(32)
    redis_client.setex(f"otp_ctx:{token}",180, email)
    return token

def get_email_url(token:str):
    email = redis_client.get(f"otp_ctx:{token}")
    return email


