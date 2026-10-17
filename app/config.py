import os
import secrets

import yaml

CONFIG_FILE = os.getenv("WAREHOUSE_CONFIG_FILE", "config.yaml")


def _load_config_file(config_path: str = CONFIG_FILE) -> dict:
    try:
        with open(config_path, "r", encoding="utf-8") as config_file:
            values = yaml.safe_load(config_file)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Configuration file not found: {config_path}") from exc
    except yaml.YAMLError as exc:
        raise RuntimeError(f"Invalid YAML in configuration file: {config_path}") from exc
    if values is None:
        return {}
    if not isinstance(values, dict):
        raise RuntimeError(f"Configuration file must contain a YAML mapping: {config_path}")
    return values

FILE_CONFIG = _load_config_file()


def _setting(file_key: str, env_key: str, default):
    value = os.getenv(env_key)
    if value is not None:
        return value
    return FILE_CONFIG.get(file_key, default)


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Expected a boolean setting, got {value!r}")


class Settings:
    PROJECT_NAME: str = "Minions Filaments Warehouse"
    VERSION: str = "1.0.0"
    SECRET_KEY: str = str(_setting("secret_key", "SECRET_KEY", "") or secrets.token_urlsafe(32))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    FEATURE_AUTH_REQUIRED: bool = _as_bool(_setting("auth_enabled", "FEATURE_AUTH_REQUIRED", True))

    # Database Configuration Parameters
    DATABASE_URL: str = _setting("database_url", "DATABASE_URL", "")
    DB_TYPE: str = str(_setting("db_type", "DB_TYPE", "sqlite"))
    DB_HOST: str = str(_setting("db_host", "DB_HOST", "localhost"))
    DB_PORT: str = str(_setting("db_port", "DB_PORT", "5432"))
    DB_USER: str = str(_setting("db_user", "DB_USER", "minion"))
    DB_PASSWORD: str = str(_setting("db_password", "DB_PASSWORD", ""))
    DB_NAME: str = str(_setting("db_name", "DB_NAME", "filaments_db"))

    # Initial Setup Admin Credentials
    DEFAULT_ADMIN_USERNAME: str = str(_setting("default_admin_username", "DEFAULT_ADMIN_USERNAME", "admin"))
    DEFAULT_ADMIN_PASSWORD: str = str(_setting("default_admin_password", "DEFAULT_ADMIN_PASSWORD", ""))
    DEFAULT_ADMIN_EMAIL: str = str(_setting("default_admin_email", "DEFAULT_ADMIN_EMAIL", "admin@example.invalid"))

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
        except yaml.YAMLError as exc:
            raise ValueError("OAUTH_PROVIDERS_YAML must contain valid YAML") from exc
        if providers is None:
            providers = {}
        if not isinstance(providers, dict):
            raise ValueError("OAuth providers configuration must be a YAML mapping")
        providers = dict(providers)
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
        if not self.DATABASE_URL:
            db_type = self.DB_TYPE.lower()
            if db_type in ("postgresql", "postgres"):
                self.DATABASE_URL = f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            elif db_type == "mysql":
                self.DATABASE_URL = f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            else:
                self.DATABASE_URL = "sqlite:///./filaments.db"

settings = Settings()
