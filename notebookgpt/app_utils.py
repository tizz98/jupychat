import pathlib
from contextlib import asynccontextmanager

import aiofiles.os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from notebookgpt.auth import jwks_client
from notebookgpt.kernels import get_nb_gpt_kernel_client
from notebookgpt.routes import api, auth, root
from notebookgpt.settings import DOMAIN, get_settings

static_directory = pathlib.Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings = get_settings()

    jwks_client.fetch_data()
    await aiofiles.os.makedirs(settings.jupyter_connection_dir, exist_ok=True)

    yield  # FastAPI running...

    # Shutdown
    await get_nb_gpt_kernel_client().shutdown_all()


def build_app():
    app = FastAPI(
        lifespan=lifespan,
        openapi_url="/openapi.json",
        servers=[{"url": DOMAIN, "description": "Notebook GPT server"}],
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://chat.openai.com", "http://localhost:8000"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    app.mount("/static", StaticFiles(directory=str(static_directory)), name="static")

    app.include_router(root.router)
    app.include_router(api.router, prefix="/api")
    app.include_router(auth.router, prefix="/oauth")

    return app
