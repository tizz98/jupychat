from fastapi import APIRouter, Security

from notebookgpt.auth import verify_jwt

router = APIRouter(dependencies=[Security(verify_jwt)])


@router.post("/run-cell")
def run_cell():
    pass  # TODO
