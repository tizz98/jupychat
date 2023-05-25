"""Taken from https://github.com/rgbkrk/dangermode/blob/main/dangermode/models.py"""
import base64
from typing import Dict, List, Optional, Tuple

from IPython import get_ipython
from jupyter_client.kernelspec import NATIVE_KERNEL_NAME
from pydantic import BaseModel, Field

from notebookgpt.settings import DOMAIN


class RunCellRequest(BaseModel):
    """A request to run a cell in the notebook."""

    kernel_id: str | None = Field(
        description="The previously created kernel_id. If not set, a new kernel will be created."
    )
    code: str = Field(description="The code to execute in the cell.")


class DisplayData(BaseModel):
    """Both display_data and execute_result messages use this format."""

    data: Optional[dict] = None
    metadata: Optional[dict] = None

    @classmethod
    def from_tuple(cls, formatted: Tuple[dict, dict]):
        return cls(data=formatted[0], metadata=formatted[1])


class ImageData(BaseModel):
    """Public URL to the image data."""

    data: bytes
    url: str


class ImageStore(BaseModel):
    """An in-memory store for images that have been displayed in the notebook."""

    image_store: Dict[str, ImageData] = {}

    def store_images(self, dd: DisplayData) -> DisplayData:
        """Convert all image/png data to URLs that the frontend can fetch"""

        if dd.data and "image/png" in dd.data:
            image_name = f"image-{len(self.image_store)}.png"
            image_data = base64.b64decode(dd.data["image/png"])

            self.image_store[image_name] = ImageData(
                data=image_data, url=f"{DOMAIN}/images/{image_name}"
            )
            dd.data["image/png"] = self.image_store[image_name].url

        return dd

    def get_image(self, image_name: str) -> bytes:
        return self.image_store[image_name].data

    def clear(self):
        self.image_store = {}


# Initialize the image store as a global instance
image_store = ImageStore()


class ErrorData(BaseModel):
    error: str

    @classmethod
    def from_exception(cls, e: Exception):
        return cls(error=str(e) if str(e) else type(e).__name__)


class RunCellResponse(BaseModel):
    """A bundle of outputs, stdout, stderr, and whether we succeeded or failed"""

    success: bool = False
    execute_result: Optional[DisplayData] = None
    error: Optional[str] = ""
    stdout: Optional[str] = ""
    stderr: Optional[str] = ""
    displays: List[DisplayData] = []
    kernel_id: str

    @classmethod
    def from_result(cls, result, stdout, stderr, displays, kernel_id: str):
        ip = get_ipython()
        if ip is None:
            return cls(success=False, error="Not running in IPython environment")

        execute_result = DisplayData.from_tuple(ip.display_formatter.format(result))
        displays = [DisplayData(data=d.data, metadata=d.metadata) for d in displays]

        # Convert all image/png data to URLs that the frontend can fetch
        displays = [image_store.store_images(d) for d in displays]
        execute_result = image_store.store_images(execute_result)

        return cls(
            success=True,
            execute_result=execute_result,
            stdout=stdout,
            stderr=stderr,
            displays=displays,
            kernel_id=kernel_id,
        )

    @classmethod
    def from_error(cls, error, kernel_id: str):
        return cls(success=False, error=f"Error executing code: {error}", kernel_id=kernel_id)


class CreateFileRequest(BaseModel):
    """A request to create a file in the notebook."""

    path: str


class CreateFileResponse(BaseModel):
    path: str


class CreateKernelRequest(BaseModel):
    kernel_name: str = Field(
        NATIVE_KERNEL_NAME, description="The kernel spec name to use to start the kernel."
    )

    @property
    def start_kernel_kwargs(self) -> dict:
        return {"kernel_name": self.kernel_name}


class CreateKernelResponse(BaseModel):
    kernel_id: str = Field(
        description="The ID of the kernel, to use for future requests related to this kernel such as running cells."
    )
