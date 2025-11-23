from db_connection.redis_config import redis_client
from dotenv import load_dotenv
import os

load_dotenv()
REDIS_EXPIRE = int(os.getenv("REDIS_EXPIRE", 300))

def save_data_redis(email: str, otp: str, data_type:str) -> bool: #data_type = [password, otp]
    try:
        redis_client.setex(f"{data_type}:{email}", REDIS_EXPIRE, otp)
        return True
    except Exception as e:
        print("Redis Save Error:", e)
        return False


def get_saved_password(email: str) -> str | None:
    try:
        return redis_client.get(f"password:{email}")
    except Exception as e:
        print("Redis Get Error:", e)
        return None


def verify_otp_redis(email: str, otp: str) -> bool:
    try:
        saved = redis_client.get(f"otp:{email}")
        if saved is None:
            return False
        return saved == otp
    except Exception as e:
        print("Redis Verification Error:", e)
        return False

def delete_data(email:str, data_type:str):
    try:
        key = f"{data_type}:{email}"
        redis_client.delete(key)
    except Exception as e:
        print("Redis Delete Error:", e)
