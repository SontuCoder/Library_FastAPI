import json
from datetime import datetime, timedelta
from uuid import uuid4

from db_connection.redis_config import redis_client

# JTI expiration = same as refresh token expiration
REFRESH_EXPIRE_DAYS = 30


def generate_jti() -> str:
    return str(uuid4())  # unique session ID


def create_session(email: str, role:str):
    now = datetime.utcnow()
    expires = now + timedelta(days=REFRESH_EXPIRE_DAYS)

    return {
        "email": email,
        "role": role,
        "created_at": now.isoformat(),
        "expires_at": expires.isoformat(),
    }


def save_jti(jti: str, session: dict):
    redis_client.setex(
        f"refresh:{jti}",
        REFRESH_EXPIRE_DAYS * 24 * 60 * 60,  # TTL in seconds
        json.dumps(session)
    )


def get_jti_session(jti: str) -> dict | None:
    data = redis_client.get(f"refresh:{jti}")
    return json.loads(data) if data else None


def validate_jti(jti: str, email: str) -> bool:
    session = get_jti_session(jti)
    if not session:
        return False
    return session["email"] == email


def delete_jti(jti: str):
    redis_client.delete(f"refresh:{jti}")


def rotate_jti(old_jti: str):
    old_session = get_jti_session(old_jti)
    if not old_session:
        raise Exception("Old session missing")
    role = old_session.get("role")
    email = old_session.get("email")
    delete_jti(old_jti)
    new_jti = generate_jti()

    session = create_session(email, role)
    save_jti(new_jti, session)

    return new_jti

