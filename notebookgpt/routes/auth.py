from urllib.parse import quote, urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from notebookgpt.settings import Settings, get_settings

router = APIRouter()


@router.get("/authorize")
def authorize(
    client_id: str, redirect_uri: str, scope: str, settings: Settings = Depends(get_settings)
):
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


@router.post("/token")
async def token(request: Request, settings: Settings = Depends(get_settings)):
    body = await request.json()
    auth0_url = f"{settings.auth0_domain}/oauth/token"

    async with httpx.AsyncClient() as client:
        resp = await client.post(auth0_url, json=body)
        if resp.is_error:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()
