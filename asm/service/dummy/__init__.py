import logging

from asm.service import Service
from asm.utils.matchers import match_service

_LOGGER = logging.getLogger(__name__)


class Dummy(Service):
    @match_service('')
    async def parse(self):
        _LOGGER.info("Dummy Service")
