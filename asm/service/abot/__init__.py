import os.path
import logging
import asyncio

from asm.service import Service
from asm.utils.matchers import match_service
from asm.service.abot.dockerspawner import DockerSpawner

_LOGGER = logging.getLogger(__name__)


class Abot(Service):
    async def setup(self):
        _LOGGER.info("Setting up the platform")
        if os.path.exists("/var/run/docker.sock"):
            spawner = DockerSpawner()

        if spawner:
            if not await spawner.exist_service("vernemq"):
                user = os.getenv('MQTT_USER', "arcus")
                password = os.getenv('MQTT_PASSWORD', "arcus")

                _LOGGER.info("Deploying VerneMQ")
                await spawner.deploy_service("vernemq",
                                             "erlio/docker-vernemq",
                                             {"DOCKER_VERNEMQ_USER_" + user.upper(): password},
                                             {},
                                             {'1883/tcp': 1883})
                _LOGGER.info("Waiting for VerneMQ")
                await asyncio.sleep(20)

    @match_service('')
    async def parse(self):
        _LOGGER.info("Service")
