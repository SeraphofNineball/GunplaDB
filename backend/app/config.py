from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://gunpla:gunplapass@localhost:5432/gunpladb"
    redis_url: str = "redis://localhost:6379/0"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin123"
    minio_bucket: str = "gunpladb"
    minio_secure: bool = False
    secret_key: str = "changeme"

    # Public URL prefix for serving stored files
    public_url: str = "http://localhost:8080"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
