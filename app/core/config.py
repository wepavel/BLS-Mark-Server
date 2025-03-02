import os

from pydantic import PostgresDsn
from pydantic import ValidationError
from pydantic import field_validator
from pydantic import ValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Any


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=['../../.env', '../.env', '.env'],
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=True,
    )

    API_V1_STR: str = '/api/v1'
    # SERVER_NAME: str
    # SERVER_HOST: AnyHttpUrl
    HOST: str = os.getenv('HOST', '127.0.0.1')
    PORT: int = os.getenv('PORT', 8001)

    PROJECT_NAME: str = os.getenv('PROJECT_NAME', 'BLS Mark Server')
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'DEBUG')
    # LOG_PATH: str = os.getenv('LOG_PATH', './logs')

    DMCODE_HANDLE_TIMEOUT: float = os.getenv('DMCODE_HANDLE_TIMEOUT', 0.5)

    SESSION_EXPIRE_MINUTES: int = 60 * 24 * 365  # 1 year

    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    SQLALCHEMY_DATABASE_URI: PostgresDsn | None = None

    @field_validator('SQLALCHEMY_DATABASE_URI', mode='before')
    def assemble_db_connection(cls, v: str | None, values: ValidationInfo) -> Any:
        if isinstance(v, str):
            return v
        return PostgresDsn.build(
            scheme='postgresql',
            username=values.data.get('POSTGRES_USER'),
            password=values.data.get('POSTGRES_PASSWORD'),
            host=values.data.get('POSTGRES_SERVER'),
            path=f"{values.data.get('POSTGRES_DB') or ''}",
        ).unicode_string()

    # Devices
    SCANNER_ADRESS: str = os.getenv('SCANNER_ADRESS', '169.254.36.51')

try:
    settings = Settings()
except ValidationError as e:
    print(e)
