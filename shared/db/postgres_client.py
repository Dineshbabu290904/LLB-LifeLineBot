import asyncpg
from typing import Optional
import logging

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None


async def get_postgres_pool(postgres_url: str) -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            postgres_url,
            min_size=2,
            max_size=10,
            command_timeout=60,
        )
        logger.info("PostgreSQL connection pool created")
    return _pool


async def close_postgres_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("PostgreSQL connection pool closed")


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(512) UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS doctor_specialties (
    id SERIAL PRIMARY KEY,
    specialty VARCHAR(100) NOT NULL,
    conditions TEXT[] DEFAULT '{}',
    urgency_levels TEXT[] DEFAULT '{}',
    telehealth_available BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS triage_rules (
    id SERIAL PRIMARY KEY,
    symptom_pattern TEXT NOT NULL,
    severity_threshold VARCHAR(50) NOT NULL,
    triage_level VARCHAR(50) NOT NULL,
    specialty VARCHAR(100),
    is_emergency BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS model_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_tag VARCHAR(50) NOT NULL,
    model_path VARCHAR(512) NOT NULL,
    model_type VARCHAR(100) NOT NULL,
    triage_accuracy FLOAT DEFAULT 0.0,
    hallucination_rate FLOAT DEFAULT 1.0,
    safety_rate FLOAT DEFAULT 0.0,
    is_active BOOLEAN DEFAULT FALSE,
    is_production BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    promoted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_model_versions_active ON model_versions(is_active);
"""


async def initialize_schema(pool: asyncpg.Pool):
    """Create all PostgreSQL tables if they don't exist."""
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA_SQL)
    logger.info("PostgreSQL schema initialized")


async def seed_doctor_specialties(pool: asyncpg.Pool):
    """Seed initial doctor specialty mappings."""
    specialties = [
        ("Emergency Medicine", ["cardiac arrest", "stroke", "trauma", "anaphylaxis"], ["EMERGENCY"], False),
        ("Cardiology", ["chest pain", "heart failure", "arrhythmia", "hypertension"], ["URGENT", "ROUTINE"], True),
        ("Neurology", ["headache", "seizure", "numbness", "memory loss"], ["URGENT", "ROUTINE"], True),
        ("Pulmonology", ["shortness of breath", "chronic cough", "asthma", "COPD"], ["URGENT", "ROUTINE"], True),
        ("Gastroenterology", ["abdominal pain", "diarrhea", "nausea", "vomiting"], ["SEMI_URGENT", "ROUTINE"], True),
        ("Orthopedics", ["joint pain", "fracture", "back pain", "sports injury"], ["SEMI_URGENT", "ROUTINE"], True),
        ("Dermatology", ["rash", "skin lesion", "acne", "eczema"], ["ROUTINE", "SELF_CARE"], True),
        ("Psychiatry", ["depression", "anxiety", "insomnia", "suicidal ideation"], ["URGENT", "ROUTINE"], True),
        ("General Practice", ["fever", "cold", "flu", "general checkup"], ["ROUTINE", "SELF_CARE"], True),
        ("Pediatrics", ["child fever", "growth concerns", "vaccination"], ["ROUTINE"], True),
        ("Endocrinology", ["diabetes", "thyroid", "hormonal imbalance"], ["ROUTINE"], True),
        ("Infectious Disease", ["infection", "HIV", "tuberculosis", "sepsis"], ["URGENT", "ROUTINE"], True),
    ]

    async with pool.acquire() as conn:
        for specialty, conditions, urgency_levels, telehealth in specialties:
            await conn.execute(
                """
                INSERT INTO doctor_specialties (specialty, conditions, urgency_levels, telehealth_available)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT DO NOTHING
                """,
                specialty, conditions, urgency_levels, telehealth
            )
    logger.info("Doctor specialties seeded")
