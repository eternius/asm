import logging

from asm.service import Service
from asm.utils.matchers import match_service

_LOGGER = logging.getLogger(__name__)


class Operator(Service):
    @match_service('')
    async def parse(self):
        _LOGGER.info("Operator Service")
