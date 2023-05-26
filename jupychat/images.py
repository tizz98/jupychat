import base64
import uuid

from jupychat.models import DisplayData, ImageData
from jupychat.settings import get_settings


class ImageStore:
    """An in-memory store for images that have been displayed in the notebook."""

    def __init__(self):
        self.image_store: dict[str, ImageData] = {}

    def store_images(self, dd: DisplayData) -> DisplayData:
        """Convert all image/png data to URLs that the frontend can fetch"""

        if dd.data and "image/png" in dd.data:
            image_name = f"image-{uuid.uuid4().hex}.png"
            image_data = base64.b64decode(dd.data["image/png"])

            self.image_store[image_name] = ImageData(
                data=image_data, url=f"{get_settings().domain}/images/{image_name}"
            )
            dd.data["image/png"] = self.image_store[image_name].url

        return dd

    def get_image(self, image_name: str) -> bytes:
        return self.image_store[image_name].data

    def clear(self):
        self.image_store = {}


# Initialize the image store as a global instance
image_store = ImageStore()
