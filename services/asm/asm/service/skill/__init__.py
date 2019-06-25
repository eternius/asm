import logging


from asm.service import Service
from asm.utils.matchers import match_webhook
from asm.utils.events import Message
from aiohttp.web import Request
from aiohttp import web

_LOGGER = logging.getLogger(__name__)


class Skill(Service):
    @match_webhook('parse')
    async def parse(self, message):
        if type(message) is not Message and type(message) is Request:
            # Capture the request POST data and set message to a default message
            request = await message.json()
            if 'text' in request:
                for nlp in self.asm.nlps:
                    for matcher in nlp.matchers:
                        if "parse_text" in matcher:
                            resp = await self.asm.run_nlp(nlp, nlp.config, request['text'])
                            return web.json_response(resp)

    @match_webhook('next_step')
    async def next_step(self, message):
        if type(message) is not Message and type(message) is Request:
            # Capture the request POST data and set message to a default message
            request = await message.json()
            for nlp in self.asm.nlps:
                for matcher in nlp.matchers:
                    if "get_response" in matcher:
                        return web.json_response(await self.asm.run_nlp(nlp, nlp.config, request))

    @match_webhook("generic_action")
    async def generic_action(self, message):
        if type(message) is not Message and type(message) is Request:
            # Capture the request POST data and set message to a default message
            request = await message.json()
            for nlp in self.asm.nlps:
                for matcher in nlp.matchers:
                    if "generic_action" in matcher:
                        return web.json_response(await self.asm.run_nlp(nlp, nlp.config, request))
