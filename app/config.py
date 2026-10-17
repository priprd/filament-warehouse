import os

import yaml

CONFIG_FILE = os.getenv("WAREHOUSE_CONFIG_FILE", "config.yaml")

def _load_config_file() -> dict:
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as config_file:
            values = yaml.safe_load(config_file)
            return values if isinstance(values, dict) else {}
    except (FileNotFoundError, yaml.YAMLError):
        return {}

FILE_CONFIG = _load_config_file()

def _setting(file_key: str, env_key: str, default):
    value = os.getenv(env_key)
    if value is not None:
        return value
    return FILE_CONFIG.get(file_key, default)

def _as_bool(value) -> bool:
    return value if isinstance(value, bool) else str(value).lower() in {"1", "true", "yes", "on"}

class Settings:
    PROJECT_NAME: str = "Minions Filaments Warehouse"
    VERSION: str = "1.0.0"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "bello_minions_secret_key_super_banana_12345")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    FEATURE_AUTH_REQUIRED: bool = _as_bool(_setting("auth_enabled", "FEATURE_AUTH_REQUIRED", True))
    
    # Database Configuration Parameters
    DB_TYPE: str = _setting("db_type", "DB_TYPE", "sqlite")
    DB_HOST: str = _setting("db_host", "DB_HOST", "localhost")
    DB_PORT: str = _setting("db_port", "DB_PORT", "5432")
    DB_USER: str = _setting("db_user", "DB_USER", "minion")
    DB_PASSWORD: str = _setting("db_password", "DB_PASSWORD", "bananapass123")
    DB_NAME: str = _setting("db_name", "DB_NAME", "filaments_db")

    # Initial Setup Admin Credentials
    DEFAULT_ADMIN_USERNAME: str = _setting("default_admin_username", "DEFAULT_ADMIN_USERNAME", "minion_master")
    DEFAULT_ADMIN_PASSWORD: str = _setting("default_admin_password", "DEFAULT_ADMIN_PASSWORD", "banana123")
    DEFAULT_ADMIN_EMAIL: str = _setting("default_admin_email", "DEFAULT_ADMIN_EMAIL", "stuart@minions-warehouse.io")

    # OAuth providers are configured in YAML so several IDPs can be enabled without code changes.
    OAUTH_PROVIDERS_YAML = _setting("oauth_providers", "OAUTH_PROVIDERS_YAML", {})
    OAUTH_REDIRECT_URI: str = _setting("oauth_redirect_uri", "OAUTH_REDIRECT_URI", "http://localhost:8000/api/auth/oauth/callback")
    GOOGLE_CLIENT_ID: str = _setting("google_client_id", "GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = _setting("google_client_secret", "GOOGLE_CLIENT_SECRET", "")

    @property
    def OAUTH_PROVIDERS(self) -> dict:
        try:
            providers = (
                self.OAUTH_PROVIDERS_YAML
                if isinstance(self.OAUTH_PROVIDERS_YAML, dict)
                else yaml.safe_load(self.OAUTH_PROVIDERS_YAML)
            )
            if not isinstance(providers, dict):
                providers = {}
        except yaml.YAMLError:
            providers = {}
        if self.GOOGLE_CLIENT_ID and "google" not in providers:
            providers["google"] = {
                "client_id": self.GOOGLE_CLIENT_ID,
                "client_secret": self.GOOGLE_CLIENT_SECRET,
                "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_url": "https://oauth2.googleapis.com/token",
                "userinfo_url": "https://openidconnect.googleapis.com/v1/userinfo",
                "scope": "openid email profile",
            }
        return providers

    def __init__(self):
        env_url = os.getenv("DATABASE_URL")
        if env_url:
            self.DATABASE_URL = env_url
        else:
            db_type = self.DB_TYPE.lower()
            if db_type in ("postgresql", "postgres"):
                self.DATABASE_URL = f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            elif db_type == "mysql":
                self.DATABASE_URL = f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            else:
                self.DATABASE_URL = "sqlite:///./filaments.db"

settings = Settings()
