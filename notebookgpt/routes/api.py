from fastapi import APIRouter, Depends, HTTPException, Security

from notebookgpt.auth import verify_jwt
from notebookgpt.kernels import NotebookGPTKernelClient, get_nb_gpt_kernel_client
from notebookgpt.models import (
    CreateKernelRequest,
    CreateKernelResponse,
    RunCellRequest,
    RunCellResponse,
)
from notebookgpt.suggestions import RUN_CELL_PARSE_FAIL

router = APIRouter(dependencies=[Security(verify_jwt)])


@router.post("/kernels")
async def create_kernel(
    request: CreateKernelRequest,
    kernel_client: NotebookGPTKernelClient = Depends(get_nb_gpt_kernel_client),
) -> CreateKernelResponse:
    """Create and start kernel with the given kernel name."""
    return await kernel_client.start_kernel(request)


@router.post("/run-cell")
async def run_cell(
    request: RunCellRequest,
    kernel_client: NotebookGPTKernelClient = Depends(get_nb_gpt_kernel_client),
) -> RunCellResponse:
    """Execute a cell and return the result.

    The execution format is:

    ```json
    {
        "kernel_id": "<previously created kernel id>",
        "code": "print('hello world')"
    }
    ```
    """

    if not request.code:
        raise HTTPException(status_code=400, detail=RUN_CELL_PARSE_FAIL)

    if not request.kernel_id:
        request.kernel_id = (await kernel_client.start_kernel(CreateKernelRequest())).kernel_id

    try:
        return await kernel_client.run_cell(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing code: {e}")
