import logging

from asm.service import Service
from asm.utils.matchers import match_service
from asm.service.abot.dockerspawner import DockerSpawner

_LOGGER = logging.getLogger(__name__)


class Abot(Service):
    async def setup(self):
        pass

    @match_service('')
    async def parse(self):
        _LOGGER.info("Service")
