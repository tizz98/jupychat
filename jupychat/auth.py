import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from starlette import status

from jupychat.settings import get_settings

jwks_client = PyJWKClient(get_settings().jwks_url, cache_keys=True)
bearer_scheme = HTTPBearer(auto_error=False)


async def optional_bearer_token(
    auth_cred: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str | None:
    return auth_cred.credentials if auth_cred else None


def verify_jwt(token: str | None = Depends(optional_bearer_token)) -> dict:
    """
    Verifies the given JWT token and returns the decoded payload.

    Parameters
    ----------
    token : str or None, optional
        The JWT token to verify, by default Depends(optional_bearer_token)

    Returns
    -------
    dict
        The decoded payload of the JWT token.

    Raises
    ------
    HTTPException
        If the token is missing or invalid.

    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization bearer token"
        )
    signing_key = jwks_client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=get_settings().oauth_audience,
    )


def optional_verify_jwt(token: str | None = Depends(optional_bearer_token)) -> dict | None:
    if not token:
        return None
    return verify_jwt(token)


def get_user_is_authenticated(token: dict | None = Depends(optional_verify_jwt)) -> bool:
    return token is not None
