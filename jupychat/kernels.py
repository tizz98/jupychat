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

from jupychat.models import (
    CreateKernelRequest,
    CreateKernelResponse,
    DisplayData,
    RunCellRequest,
    RunCellResponse,
    image_store,
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
        kernel_id = await self._mkm.start_kernel(**request.start_kernel_kwargs)
        logger.info("Started kernel", kernel_id=kernel_id)
        connection_info = self._mkm.get_connection_info(kernel_id)
        self._sidecar_clients[kernel_id] = KernelSidecarClient(connection_info=connection_info)
        await self._sidecar_clients[kernel_id].__aenter__()
        return CreateKernelResponse(kernel_id=kernel_id)

    async def run_cell(self, request: RunCellRequest) -> RunCellResponse:
        sidecar_client = self._sidecar_clients[request.kernel_id]
        output_handler = JupyChatOutputHandler(sidecar_client, uuid.uuid4().hex)
        status_handler = StatusHandler()
        await sidecar_client.execute_request(
            request.code, handlers=[output_handler, status_handler]
        )
        return output_handler.to_response(status_handler, request.kernel_id)

    async def shutdown_all(self) -> None:
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

    async def add_cell_content(self, content: ContentType):
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
