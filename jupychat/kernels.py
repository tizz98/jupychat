"""
This module contains the client classes for managing Jupyter kernels.

Classes:
- JupyChatKernelClient: A client class for managing Jupyter kernels.
- JupyChatOutputHandler: A custom output handler for Jupyter kernels that formats the output for use in JupyChat.
- StatusHandler: A custom status handler for Jupyter kernels that tracks the status of cell execution.
"""
import uuid
from functools import lru_cache

import structlog
from IPython import get_ipython
from IPython.terminal.embed import InteractiveShellEmbed
from jupyter_client import AsyncMultiKernelManager
from kernel_sidecar.client import KernelSidecarClient
from kernel_sidecar.handlers.base import Handler
from kernel_sidecar.handlers.output import ContentType, OutputHandler
from kernel_sidecar.models import messages
from kernel_sidecar.models.messages import CellStatus, StreamChannel

from jupychat.images import image_store
from jupychat.models import (
    CreateKernelRequest,
    CreateKernelResponse,
    DisplayData,
    RunCellRequest,
    RunCellResponse,
)
from jupychat.settings import get_settings

logger = structlog.get_logger(__name__)


def safe_get_ipython():
    """Get an ipython shell instance for use with formatting."""
    if ip := get_ipython():
        return ip
    return InteractiveShellEmbed()


class JupyChatKernelClient:
    """Client class for managing jupyter kernels.

    This wraps the jupyter multi kernel manager and provides a simple
    interface for managing kernels.
    """

    def __init__(self, mkm: AsyncMultiKernelManager) -> None:
        self._mkm = mkm
        self._sidecar_clients: dict[str, KernelSidecarClient] = {}

    async def start_kernel(self, request: CreateKernelRequest) -> CreateKernelResponse:
        """
        Starts a new kernel with the given arguments and returns its ID.

        Parameters
        ----------
        request : CreateKernelRequest
            A `CreateKernelRequest` object containing the arguments for starting the kernel.

        Returns
        -------
        CreateKernelResponse
            A `CreateKernelResponse` object containing the ID of the newly created kernel.

        Raises
        ------
        Any exceptions raised by the `start_kernel` method of the `MultiKernelManager` object.

        """
        kernel_id = await self._mkm.start_kernel(**request.start_kernel_kwargs)
        logger.info("Started kernel", kernel_id=kernel_id)
        connection_info = self._mkm.get_connection_info(kernel_id)
        self._sidecar_clients[kernel_id] = KernelSidecarClient(connection_info=connection_info)
        await self._sidecar_clients[kernel_id].__aenter__()
        return CreateKernelResponse(kernel_id=kernel_id)

    async def run_cell(self, request: RunCellRequest) -> RunCellResponse:
        """
        Executes the given code in the kernel associated with the given ID and returns the output.

        Parameters
        ----------
        request : RunCellRequest
            A `RunCellRequest` object containing the code to execute and the ID of the kernel to use.

        Returns
        -------
        RunCellResponse
            A `RunCellResponse` object containing the output of the executed code.

        Raises
        ------
        Any exceptions raised by the `execute_request` method of the `KernelSidecarClient` object.

        """

        sidecar_client = self._sidecar_clients[request.kernel_id]
        output_handler = JupyChatOutputHandler(sidecar_client, uuid.uuid4().hex)
        status_handler = StatusHandler()
        await sidecar_client.execute_request(
            request.code, handlers=[output_handler, status_handler]
        )
        return output_handler.to_response(status_handler, request.kernel_id)

    async def shutdown_all(self) -> None:
        """
        Shuts down all running kernels and their associated sidecar clients.

        Raises
        ------
        Any exceptions raised by the `__aexit__` method of the `KernelSidecarClient` object or the `shutdown_kernel` method
        of the `MultiKernelManager` object.

        """
        for kernel_id, sidecar_client in self._sidecar_clients.items():
            await sidecar_client.__aexit__(None, None, None)
            await self._mkm.shutdown_kernel(kernel_id, now=True)
            logger.info("Shut down kernel", kernel_id=kernel_id)


class JupyChatOutputHandler(OutputHandler):
    def __init__(self, client: KernelSidecarClient, cell_id: str):
        super().__init__(client, cell_id)

        self.stdout = []
        self.stderr = []
        self.displays = []
        self.execute_result_data = None
        self.error_in_exec = None

    async def add_cell_content(self, content: ContentType) -> None:
        """
        Adds the given content to the output of the cell.

        Parameters
        ----------
        content : ContentType
            The content to add to the output of the cell.

        Returns
        -------
        None

        """

        match type(content):
            case messages.StreamContent:
                if content.name == StreamChannel.stdout:
                    self.stdout.append(content.text)
                elif content.name == StreamChannel.stderr:
                    self.stderr.append(content.text)
            case messages.ExecuteResultContent:
                self.execute_result_data = content.data
            case messages.DisplayDataContent:
                self.displays.append((content.data, content.metadata))
            case messages.ErrorContent:
                self.error_in_exec = f"{content.ename}: {content.evalue}"
            case _:
                logger.warning("Unknown content type", content=content)

    def to_response(self, status: "StatusHandler", kernel_id: str) -> RunCellResponse:
        """
        Converts the output of the cell to a `RunCellResponse` object.

        Parameters
        ----------
        status : StatusHandler
            The `StatusHandler` object containing the status of the executed cell.
        kernel_id : str
            The ID of the kernel that executed the cell.

        Returns
        -------
        RunCellResponse
            A `RunCellResponse` object containing the output of the executed cell.

        """
        ip = safe_get_ipython()

        execute_result = None
        if self.execute_result_data:
            formatted = ip.display_formatter.format(self.execute_result_data)
            execute_result = DisplayData.from_tuple(formatted)
            execute_result = image_store.store_images(execute_result)

        displays = [DisplayData(data=data, metadata=metadata) for data, metadata in self.displays]
        displays = [image_store.store_images(d) for d in displays]

        return RunCellResponse(
            success=status.execute_reply_status == CellStatus.ok,
            kernel_id=kernel_id,
            error=self.error_in_exec,
            stdout="".join(self.stdout),
            stderr="".join(self.stderr),
            execute_result=execute_result,
            displays=displays,
        )


class StatusHandler(Handler):
    def __init__(self):
        super().__init__()
        self.execute_reply_status: CellStatus = CellStatus.error

    async def handle_execute_reply(self, msg: messages.ExecuteReply) -> None:
        self.execute_reply_status = msg.content.status


@lru_cache(maxsize=1)
def get_nb_gpt_kernel_client() -> JupyChatKernelClient:
    settings = get_settings()
    mkm = AsyncMultiKernelManager(connection_dir=settings.jupyter_connection_dir)
    return JupyChatKernelClient(mkm)
