"""Taken from https://github.com/rgbkrk/dangermode/blob/main/dangermode/models.py"""
import base64
from typing import Dict, List, Optional, Tuple

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


class ImageStore:
    """An in-memory store for images that have been displayed in the notebook."""

    def __init__(self):
        self.image_store: Dict[str, ImageData] = {}

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


class RunCellResponse(BaseModel):
    """A bundle of outputs, stdout, stderr, and whether we succeeded or failed"""

    success: bool = False
    execute_result: Optional[DisplayData] = None
    error: Optional[str] = ""
    stdout: Optional[str] = ""
    stderr: Optional[str] = ""
    displays: List[DisplayData] = []
    kernel_id: str


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
