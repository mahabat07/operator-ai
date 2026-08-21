from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    ENV: str = "development"
    API_PREFIX: str = "/api/v1"

    DATABASE_URL: str = "postgresql+asyncpg://operator:operator@db:5432/operator_ai"
    REDIS_URL: str = "redis://redis:6379/0"

    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"

    ENCRYPTION_KEY: str | None = None
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30


    AI_PROVIDER: str = "none"
    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str = "https://api.groq.com/openai/v1"
    OPENAI_MODEL: str = "llama-3.3-70b-versatile"
    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    OLLAMA_MODEL: str = "qwen2.5-coder:1.5b"


    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:3000/oauth/callback"
    GOOGLE_INTEGRATION_REDIRECT_URI: str = "http://localhost:3001/oauth/google/callback"

    GOOGLE_SCOPES: str = (
        "openid email profile "
        "https://www.googleapis.com/auth/gmail.readonly "
        "https://www.googleapis.com/auth/gmail.send "
        "https://www.googleapis.com/auth/calendar.readonly "
        "https://www.googleapis.com/auth/drive.readonly"
    )

    FRONTEND_URL: str = "http://localhost:3000"


settings = Settings()
