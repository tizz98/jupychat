from urllib.parse import quote, urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from jupychat.settings import Settings, get_settings

router = APIRouter()


@router.get("/authorize", include_in_schema=False)
def authorize(
    client_id: str, redirect_uri: str, scope: str, settings: Settings = Depends(get_settings)
):
    """
    Redirects the user to the Auth0 authorization page with the given query parameters.

    Parameters
    ----------
    client_id : str
        The client ID of the application.
    redirect_uri : str
        The URI to redirect to after the user has authorized the application.
    scope : str
        The scopes to request from the user.
    settings : Settings, optional
        The application settings, by default Depends(get_settings)

    Returns
    -------
    Response
        A `Response` object with a 302 status code and a `Location` header pointing to the Auth0 authorization page.

    """

    # Redirect with the correct query parameters
    auth0_args = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "audience": settings.oauth_audience,
    }
    return Response(
        status_code=status.HTTP_302_FOUND,
        headers={
            "Location": f"{settings.auth0_domain}/authorize?{urlencode(auth0_args, quote_via=quote)}"  # noqa: E501
        },
    )


@router.post("/token", include_in_schema=False)
async def token(request: Request, settings: Settings = Depends(get_settings)):
    """
    Retrieves an access token from Auth0 using the provided credentials.

    Parameters
    ----------
    request : Request
        The incoming HTTP request.
    settings : Settings, optional
        The application settings, by default Depends(get_settings)

    Returns
    -------
    Union[Dict[str, Any], HTTPException]
        A dictionary containing the access token and other information if the request was successful, or an
        `HTTPException` if the request failed.

    """
    body = await request.json()
    auth0_url = f"{settings.auth0_domain}/oauth/token"

    async with httpx.AsyncClient() as client:
        resp = await client.post(auth0_url, json=body)
        if resp.is_error:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()
