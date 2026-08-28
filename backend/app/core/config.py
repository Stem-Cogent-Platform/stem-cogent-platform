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
    FRONTEND_PUBLIC_URL: str = "http://localhost:3000"
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
    DATABASE_RUNTIME_ROLE: str = "sc_app_runtime"

    REDIS_HOST: str | None = None
    REDIS_PORT: int = 6379
    REDIS_URL: str | None = None
    REDIS_TLS_ENABLED: bool = True

    SQS_INGESTION_PRIORITY_URL: str | None = None
    SQS_INGESTION_STANDARD_URL: str | None = None
    SQS_PIPELINE_RAW_SIGNALS_URL: str | None = None
    SQS_PIPELINE_VALIDATED_URL: str | None = None
    SQS_PIPELINE_NORMALIZED_URL: str | None = None
    SQS_PIPELINE_CLASSIFIED_URL: str | None = None
    SQS_PIPELINE_ENRICHED_URL: str | None = None
    SQS_PIPELINE_SCORED_URL: str | None = None
    SQS_PIPELINE_CLUSTERED_URL: str | None = None
    SQS_PIPELINE_SYNTHESIZED_URL: str | None = None
    SQS_PIPELINE_RECOMMENDED_URL: str | None = None
    SQS_PIPELINE_ALERTS_URL: str | None = None
    SQS_PIPELINE_SUSPICIOUS_URL: str | None = None
    SQS_CLASSIFICATION_REVIEW_URL: str | None = None
    SQS_ENTITY_REVIEW_URL: str | None = None
    SQS_FEEDBACK_EVENTS_URL: str | None = None
    SQS_GRAPH_UPDATES_URL: str | None = None

    S3_RAW_SIGNALS_BUCKET: str | None = None
    S3_ENTERPRISE_UPLOADS_BUCKET: str | None = None
    S3_ML_ARTEFACTS_BUCKET: str | None = None

    TAXONOMY_CACHE_TTL_SECONDS: float = 30.0
    CLASSIFICATION_REVIEW_THRESHOLD: float = 0.65

    EMBEDDING_PROVIDER: str = "openai"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536
    EMBEDDING_MAX_INPUT_CHARACTERS: int = 12_000
    EMBEDDING_TIMEOUT_SECONDS: float = 30.0
    EMBEDDING_MAX_RETRIES: int = 4
    SEMANTIC_DEDUP_DISTANCE_THRESHOLD: float = 0.08
    SEMANTIC_CLUSTER_DISTANCE_THRESHOLD: float = 0.18
    SEMANTIC_HISTORY_DAYS: int = 365
    SEMANTIC_SEARCH_LIMIT: int = 10

    LLM_PRIMARY_PROVIDER: str = "openai"
    LLM_PRIMARY_MODEL: str = "gpt-5-mini"
    LLM_TIMEOUT_SECONDS: float = 45.0
    LLM_MAX_RETRIES: int = 4
    GLOBAL_SYNTHESIS_PROMPT_VERSION: str = "2026.08-v2"
    APPLICATION_VERSION: str = "0.1.0"

    DATABASE_CREDENTIALS_ARN: str | None = None
    REDIS_AUTH_TOKEN_ARN: str | None = None
    JWT_SIGNING_SECRET_ARN: str | None = None
    OPENAI_API_KEY_ARN: str | None = None
    GROQ_API_KEY_ARN: str | None = None
    RESEND_API_KEY_ARN: str | None = None
    PAYSTACK_SECRET_KEY_ARN: str | None = None
    PAYSTACK_PUBLIC_KEY_ARN: str | None = None
    PAYSTACK_WEBHOOK_SECRET_ARN: str | None = None
    GOOGLE_OAUTH_CREDENTIALS_ARN: str | None = None
    LINKEDIN_OAUTH_CREDENTIALS_ARN: str | None = None
    CBN_USD_NGN_RATE_URL: str = "https://www.cbn.gov.ng/api/GetNFEM_Rates_TOP"
    FX_QUOTE_TIMEOUT_SECONDS: float = 15.0

    SYNTHESIS_ENABLED: bool = True
    CIL_ENABLED: bool = True
    CLICKHOUSE_ENABLED: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
