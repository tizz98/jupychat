from functools import lru_cache

from pydantic import BaseSettings


class Settings(BaseSettings):
    domain: str = "http://localhost:8000"

    @property
    def logo_url(self):
        return f"{self.domain}/static/images/logo3.png"

    @property
    def openapi_url(self):
        return f"{self.domain}/openapi.json"

    @property
    def oauth_client_url(self):
        return f"{self.domain}/oauth/authorize"

    @property
    def oauth_authorization_url(self):
        return f"{self.domain}/oauth/token"

    openai_verification_token: str = "unset"

    auth0_domain: str
    jwks_url: str
    jwks_cache_time_sec: int = 300

    oauth_audience: str = "https://example.com/jupychat"

    jupyter_connection_dir: str = "/tmp/jupychat_connection_files"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
