from functools import lru_cache

from pydantic import BaseSettings


class Settings(BaseSettings):
    openapi_url: str = "http://localhost:8000/openapi.json"
    oauth_client_url: str = "http://localhost:8000/oauth/authorize"
    oauth_authorization_url: str = "http://localhost:8000/oauth/token"
    openai_verification_token: str = "unset"

    jwks_url: str = "https://chatgpt-plugin-demo.us.auth0.com/.well-known/jwks.json"
    jwks_cache_time_sec: int = 300

    oauth_audience: str = "https://notebookgpt"


@lru_cache()
def get_settings():
    return Settings()
