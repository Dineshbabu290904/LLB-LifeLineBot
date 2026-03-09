from setuptools import setup, find_packages

setup(
    name="medbot-shared",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
        "motor>=3.3.0",
        "asyncpg>=0.29.0",
        "aioredis>=2.0.0",
        "httpx>=0.26.0",
    ],
    python_requires=">=3.11",
)
