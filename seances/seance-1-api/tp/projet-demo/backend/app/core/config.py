from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    test_database_url: str | None = None
    jwt_secret: str                 # obligatoire : pas de valeur par défaut
    jwt_expire_minutes: int = 60
    sql_echo: bool = False


settings = Settings()
