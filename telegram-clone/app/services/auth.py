import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))



def create_access_token(user_id: uuid.UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


# 创建 JWT access token。
# expire：当前 UTC 时间加上配置的过期分钟数。
# payload 包含 sub（subject，通常存放用户标识）和 exp（过期时间）。
# jwt.encode 使用配置的 secret_key 和算法（如 HS256）签名，返回字符串 token



def decode_access_token(token: str) -> uuid.UUID | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return uuid.UUID(user_id)
    except (JWTError, ValueError):
        return None


# 解码 token，验证签名和过期时间。
# 如果成功，从 payload 中取出 sub（用户 ID 字符串），转为 uuid.UUID 返回。
# 如果失败（JWTError 或 ValueError），返回 None。后者可能由于字符串不是合法的 UUID 格式。



async def get_current_user(db: AsyncSession, token: str) -> User | None:
    user_id = decode_access_token(token)
    if user_id is None:
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

# 从 token 中解析出 user_id，然后查询数据库返回 User 对象（如果存在）。
#
# scalar_one_or_none() 返回一条记录，如果没有则返回 None。
#
# 这个函数通常被 api/deps.py 中的 require_user 依赖使用，用于保护需要登录的路由。