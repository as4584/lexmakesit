"""
Centralized configuration module for AI Receptionist.

This module loads all configuration from environment variables
without hardcoding any sensitive values.
"""

from typing import Optional
import logging

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    from pydantic import Field
except ImportError:
    from pydantic import BaseSettings, Field
    SettingsConfigDict = None

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.
    
    All sensitive values are loaded from environment, never hardcoded.
    """
    
    # Application Environment
    app_env: str = Field(default="local", validation_alias="ENVIRONMENT")
    debug: bool = False
    
    # Twilio Configuration (loaded from environment only)
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_phone_number: Optional[str] = None
    
    # Database Configuration
    database_url: Optional[str] = None
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "ai_receptionist"
    postgres_user: Optional[str] = None
    postgres_password: Optional[str] = None
    
    # Redis Configuration
    redis_url: Optional[str] = None
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = None
    
    # Admin/Security
    admin_private_key: Optional[str] = None
    
    # Application Settings
    log_level: str = "INFO"
    
    if SettingsConfigDict:
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            env_prefix="",
            case_sensitive=False,
            extra="ignore"
        )
    else:
        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"
            case_sensitive = False
            extra = "ignore"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app_env.lower() in ["local", "development", "dev"]
    
    def get_database_url(self) -> Optional[str]:
        """
        Get database URL, constructing from components if DATABASE_URL not set.
        
        Returns:
            Database connection string or None if not configured
        """
        if self.database_url:
            return self.database_url
        
        if self.postgres_user and self.postgres_password:
            return (
                f"postgresql://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )
        
        return None
    
    def get_redis_url(self) -> str:
        """
        Get Redis URL, constructing from components if REDIS_URL not set.
        
        Returns:
            Redis connection string
        """
        if self.redis_url:
            return self.redis_url
        
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    def validate_twilio_config(self) -> bool:
        """
        Validate that required Twilio configuration is present.
        
        Returns:
            True if Twilio is properly configured
        """
        return all([
            self.twilio_account_sid,
            self.twilio_auth_token,
            self.twilio_phone_number
        ])
    
    def configure_logging(self) -> None:
        """Configure application logging based on settings."""
        log_level = getattr(logging, self.log_level.upper(), logging.INFO)
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        if self.is_development:
            logging.getLogger('ai_receptionist').setLevel(logging.DEBUG)


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get or create the global settings instance.
    
    Returns:
        Settings instance loaded from environment
    """
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.configure_logging()
        logger.info(f"Settings loaded for environment: {_settings.app_env}")
    return _settings


def reset_settings() -> None:
    """Reset settings instance (mainly for testing)."""
    global _settings
    _settings = None
