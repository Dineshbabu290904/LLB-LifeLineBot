import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import asyncpg
import bcrypt
import jwt
from pydantic import BaseModel, EmailStr
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql://medbot:medbot@postgres:5432/medbot"
    )
    jwt_secret: str = os.getenv("JWT_SECRET", "super-secret-jwt-key-change-in-production")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    class Config:
        env_file = ".env"


settings = Settings()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


class TokenVerify(BaseModel):
    token: str


class TokenRefresh(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    user_id: str
    email: str
    full_name: Optional[str]
    created_at: datetime


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class AuthService:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    # ------------------------------------------------------------------
    # DB bootstrap
    # ------------------------------------------------------------------

    async def init_db(self):
        """Create the connection pool and ensure the users table exists."""
        try:
            self.pool = await asyncpg.create_pool(
                settings.database_url,
                min_size=2,
                max_size=10,
                command_timeout=30,
            )
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        user_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        email       TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        full_name   TEXT,
                        is_active   BOOLEAN DEFAULT TRUE,
                        created_at  TIMESTAMPTZ DEFAULT NOW(),
                        updated_at  TIMESTAMPTZ DEFAULT NOW()
                    )
                    """
                )
                await conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS refresh_tokens (
                        token_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id     UUID REFERENCES users(user_id) ON DELETE CASCADE,
                        token_hash  TEXT UNIQUE NOT NULL,
                        expires_at  TIMESTAMPTZ NOT NULL,
                        revoked     BOOLEAN DEFAULT FALSE,
                        created_at  TIMESTAMPTZ DEFAULT NOW()
                    )
                    """
                )
            logger.info("Database initialised successfully.")
        except Exception as exc:
            logger.error("Failed to initialise database: %s", exc)
            # Allow startup without DB so health check still works
            self.pool = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _hash_password(self, plain: str) -> str:
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(plain.encode(), salt).decode()

    def _verify_password(self, plain: str, hashed: str) -> bool:
        return bcrypt.checkpw(plain.encode(), hashed.encode())

    def _create_access_token(self, user_id: str, email: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "email": email,
            "iat": now,
            "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
            "type": "access",
        }
        return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    def _create_refresh_token(self, user_id: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "iat": now,
            "exp": now + timedelta(days=settings.refresh_token_expire_days),
            "jti": str(uuid.uuid4()),
            "type": "refresh",
        }
        return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    def _decode_token(self, token: str) -> dict:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )

    # ------------------------------------------------------------------
    # Business logic
    # ------------------------------------------------------------------

    async def register(self, data: UserCreate) -> UserResponse:
        if not self.pool:
            raise RuntimeError("Database unavailable")

        async with self.pool.acquire() as conn:
            existing = await conn.fetchrow(
                "SELECT user_id FROM users WHERE email = $1", data.email
            )
            if existing:
                raise ValueError("Email already registered")

            password_hash = self._hash_password(data.password)
            row = await conn.fetchrow(
                """
                INSERT INTO users (email, password_hash, full_name)
                VALUES ($1, $2, $3)
                RETURNING user_id, email, full_name, created_at
                """,
                data.email,
                password_hash,
                data.full_name,
            )

        return UserResponse(
            user_id=str(row["user_id"]),
            email=row["email"],
            full_name=row["full_name"],
            created_at=row["created_at"],
        )

    async def login(self, data: UserLogin) -> TokenResponse:
        if not self.pool:
            raise RuntimeError("Database unavailable")

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT user_id, email, password_hash, is_active FROM users WHERE email = $1",
                data.email,
            )
            if not row or not row["is_active"]:
                raise ValueError("Invalid credentials")
            if not self._verify_password(data.password, row["password_hash"]):
                raise ValueError("Invalid credentials")

            user_id = str(row["user_id"])
            access_token = self._create_access_token(user_id, row["email"])
            refresh_token = self._create_refresh_token(user_id)

            # Store hashed refresh token
            token_hash = bcrypt.hashpw(
                refresh_token.encode(), bcrypt.gensalt(rounds=10)
            ).decode()
            expires_at = datetime.now(timezone.utc) + timedelta(
                days=settings.refresh_token_expire_days
            )
            await conn.execute(
                """
                INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
                VALUES ($1, $2, $3)
                """,
                row["user_id"],
                token_hash,
                expires_at,
            )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.access_token_expire_minutes * 60,
        )

    async def verify(self, data: TokenVerify) -> dict:
        try:
            payload = self._decode_token(data.token)
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as exc:
            raise ValueError(f"Invalid token: {exc}")

        if payload.get("type") != "access":
            raise ValueError("Not an access token")

        return {
            "valid": True,
            "user_id": payload["sub"],
            "email": payload["email"],
            "expires_at": datetime.fromtimestamp(payload["exp"], tz=timezone.utc).isoformat(),
        }

    async def refresh(self, data: TokenRefresh) -> TokenResponse:
        try:
            payload = self._decode_token(data.refresh_token)
        except jwt.ExpiredSignatureError:
            raise ValueError("Refresh token has expired")
        except jwt.InvalidTokenError as exc:
            raise ValueError(f"Invalid token: {exc}")

        if payload.get("type") != "refresh":
            raise ValueError("Not a refresh token")

        user_id = payload["sub"]

        if not self.pool:
            raise RuntimeError("Database unavailable")

        async with self.pool.acquire() as conn:
            # Verify user still active
            row = await conn.fetchrow(
                "SELECT email, is_active FROM users WHERE user_id = $1",
                uuid.UUID(user_id),
            )
            if not row or not row["is_active"]:
                raise ValueError("User not found or inactive")

            # Issue new tokens
            new_access = self._create_access_token(user_id, row["email"])
            new_refresh = self._create_refresh_token(user_id)

            token_hash = bcrypt.hashpw(
                new_refresh.encode(), bcrypt.gensalt(rounds=10)
            ).decode()
            expires_at = datetime.now(timezone.utc) + timedelta(
                days=settings.refresh_token_expire_days
            )
            await conn.execute(
                """
                INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
                VALUES ($1, $2, $3)
                """,
                uuid.UUID(user_id),
                token_hash,
                expires_at,
            )

        return TokenResponse(
            access_token=new_access,
            refresh_token=new_refresh,
            expires_in=settings.access_token_expire_minutes * 60,
        )
