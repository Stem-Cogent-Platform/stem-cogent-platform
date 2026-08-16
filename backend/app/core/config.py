from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENVIRONMENT: str = "development"
    SERVICE_NAME: str = "sc-api-service"
    AWS_REGION: str = "eu-west-1"
    LOG_LEVEL: str = "INFO"
    XRAY_ENABLED: bool = False
    XRAY_DAEMON_ADDRESS: str = "127.0.0.1:2000"

    DATABASE_HOST: str | None = None
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "stemcogent"
    DATABASE_REPLICA_HOST: str | None = None
    DATABASE_URL: str | None = None
    DATABASE_SSL_MODE: str = "require"

    REDIS_HOST: str | None = None
    REDIS_PORT: int = 6379
    REDIS_URL: str | None = None
    REDIS_TLS_ENABLED: bool = True

    SQS_INGESTION_PRIORITY_URL: str | None = None
    SQS_PIPELINE_RAW_SIGNALS_URL: str | None = None
    SQS_PIPELINE_VALIDATED_URL: str | None = None

    S3_RAW_SIGNALS_BUCKET: str | None = None
    S3_ENTERPRISE_UPLOADS_BUCKET: str | None = None
    S3_ML_ARTEFACTS_BUCKET: str | None = None

    DATABASE_CREDENTIALS_ARN: str | None = None
    REDIS_AUTH_TOKEN_ARN: str | None = None
    JWT_SIGNING_SECRET_ARN: str | None = None
    OPENAI_API_KEY_ARN: str | None = None
    GROQ_API_KEY_ARN: str | None = None
    RESEND_API_KEY_ARN: str | None = None
    PAYSTACK_SECRET_KEY_ARN: str | None = None
    PAYSTACK_PUBLIC_KEY_ARN: str | None = None
    PAYSTACK_WEBHOOK_SECRET_ARN: str | None = None

    SYNTHESIS_ENABLED: bool = True
    CIL_ENABLED: bool = True
    CLICKHOUSE_ENABLED: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
