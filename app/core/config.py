import os

from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    HOST: str = os.getenv('HOST', '0.0.0.0')
    PORT: int = os.getenv('PORT', 8001)

    PROJECT_NAME: str = 'BLS Mark Server'
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'DEBUG')
    # LOG_PATH: str = os.getenv('LOG_PATH', './logs')

    SESSION_EXPIRE_MINUTES: int = 60 * 24 * 365  # 1 year


try:
    settings = Settings()
except ValidationError as e:
    print(e)
