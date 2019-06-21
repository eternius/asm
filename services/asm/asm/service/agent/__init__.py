import logging

from asm.service import Service
from asm.utils.matchers import match_service

_LOGGER = logging.getLogger(__name__)


class Agent(Service):
    async def setup(self):
        pass

    @match_service('')
    async def parse(self, message):
        await message.respond("I can't check the billing API without a key.")
