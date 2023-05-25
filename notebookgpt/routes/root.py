"""Root-level routes."""

import yaml
from fastapi import APIRouter, Depends
from fastapi.templating import Jinja2Templates
from jinja2 import Template

from notebookgpt.settings import Settings, get_settings

router = APIRouter()

templates = Jinja2Templates(directory="notebookgpt/templates")


@router.get("/.well-known/ai-plugin.json", include_in_schema=False)
def get_ai_plugin_json(settings: Settings = Depends(get_settings)):
    template: Template = templates.get_template("ai-plugin.yaml")
    template_context = {
        "OPENAPI_URL": settings.openapi_url,
        "OAUTH_CLIENT_URL": settings.oauth_client_url,
        "OAUTH_AUTHORIZATION_URL": settings.oauth_authorization_url,
        "OPENAI_VERIFICATION_TOKEN": settings.openai_verification_token,
        "user_is_authenticated": False,
    }
    rendered_template = template.render(**template_context)
    return yaml.safe_load(rendered_template)
