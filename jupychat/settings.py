import os
from functools import lru_cache

from pydantic import BaseSettings

DOMAIN = os.environ.get("JUPYCHAT_DOMAIN", "http://localhost:8000")


class Settings(BaseSettings):
    logo_url: str = f"{DOMAIN}/static/images/logo.png"
    openapi_url: str = f"{DOMAIN}/openapi.json"
    oauth_client_url: str = f"{DOMAIN}/oauth/authorize"
    oauth_authorization_url: str = f"{DOMAIN}/oauth/token"
    openai_verification_token: str = "unset"

    auth0_domain: str = "https://chatgpt-plugin-demo.us.auth0.com"
    jwks_url: str = "https://chatgpt-plugin-demo.us.auth0.com/.well-known/jwks.json"
    jwks_cache_time_sec: int = 300

    oauth_audience: str = "https://example.com/jupychat"

    jupyter_connection_dir: str = "/tmp/jupychat_connection_files"


@lru_cache()
def get_settings():
    return Settings()
