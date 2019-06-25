import logging
import aiohttp

from asm.service import Service
from asm.utils.matchers import match_service

_LOGGER = logging.getLogger(__name__)


class Agent(Service):
    async def setup(self):
        pass

    @match_service('')
    async def parse(self, message):
        best_skill = None
        best_skill_data = None
        for skill in self.config['skills']:
            async with aiohttp.ClientSession() as session:
                async with session.post('http://skill-' + skill + ":8080/api/v1/skill/parse",
                                        json={'text': message.text}) as resp:
                    result = await resp.json()
                    if best_skill is None or result['intent']['confidence'] > best_skill['intent']['confidence']:
                        best_skill = skill
                        best_skill_data = result

        best_skill_data['user'] = message.user
        best_skill_data['channel'] = message.connector.name

        async with aiohttp.ClientSession() as session:
            async with session.post('http://skill-' + best_skill + ":8080/api/v1/skill/next_step",
                                    json=best_skill_data) as resp:
                result = await resp.json()
                await message.respond(result['text'])
