import pathlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from notebookgpt.routes import api, root

static_directory = pathlib.Path(__file__).parent / "static"


def build_app():
    app = FastAPI(
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

    return app
