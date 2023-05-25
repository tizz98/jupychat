import pathlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from notebookgpt.auth import jwks_client
from notebookgpt.routes import api, auth, root

static_directory = pathlib.Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    jwks_client.fetch_data()
    yield


def build_app():
    app = FastAPI(
        lifespan=lifespan,
        openapi_url="/openapi.json",
        servers=[{"url": "http://localhost:8000", "description": "Notebook GPT server"}],
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://chat.openai.com"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    app.mount("/static", StaticFiles(directory=str(static_directory)), name="static")

    app.include_router(root.router)
    app.include_router(api.router, prefix="/api")
    app.include_router(auth.router, prefix="/oauth")

    return app
