from jose import jwt, JWTError, ExpiredSignatureError
from datetime import datetime, timedelta
from uuid import uuid4
from dotenv import load_dotenv
import os

load_dotenv()

ACCESS_SECRET = os.getenv("ACCESS_SECRET")
REFRESH_SECRET = os.getenv("REFRESS_SECRET")
ALGORITHM = "HS256"

ACCESS_EXPIRE_MINUTES = 15        # short-lived
REFRESH_EXPIRE_DAYS = 30          # long-lived


def create_access_token(email: str, role:str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_EXPIRE_MINUTES)

    payload = {
        "email": email,
        "type": "access",
        "exp": expire,
        "role":role,
        "iat": datetime.utcnow(),
    }

    return jwt.encode(payload, ACCESS_SECRET, algorithm=ALGORITHM)


def create_refresh_token(email: str, jti: str) -> str:
    expire = datetime.utcnow() + timedelta(days=REFRESH_EXPIRE_DAYS)

    payload = {
        "email": email,
        "type": "refresh",
        "jti": jti,                      # Unique session ID
        "exp": expire,
        "iat": datetime.utcnow(),
    }

    return jwt.encode(payload, REFRESH_SECRET, algorithm=ALGORITHM)


def verify_access_token(token: str):
    try:
        payload = jwt.decode(token, ACCESS_SECRET, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise Exception("Invalid token type")
        return payload

    except ExpiredSignatureError:
        raise Exception("Access token expired")

    except JWTError:
        raise Exception("Invalid access token")


def verify_refresh_token(token: str):
    try:
        payload = jwt.decode(token, REFRESH_SECRET, algorithms=[ALGORITHM])

        if payload.get("type") != "refresh":
            raise Exception("Invalid token type")

        if "jti" not in payload:
            raise Exception("Invalid refresh token")

        return payload 

    except ExpiredSignatureError:
        raise Exception("Refresh token expired")

    except JWTError:
        raise Exception("Invalid refresh token")

