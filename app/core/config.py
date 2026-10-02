from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://postgres:postgres@localhost:5432/eve"
    secret_key: str = "dev-secret-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    bcrypt_rounds: int = 12
    # Shared secret used to sign webhook bodies (HMAC-SHA256).
    webhook_secret: str = "dev-webhook-secret"
    # Probability that a mock payment succeeds when no outcome is forced.
    mock_payment_success_rate: float = 0.8


settings = Settings()
