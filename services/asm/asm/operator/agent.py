import logging
import asyncio
import random
import string

from asm.operator.platform import Platform
from asm.operator.skill import Skill
from matrix_client.client import MatrixClient, MatrixRequestError

_LOGGER = logging.getLogger(__name__)


class Agent:
    def __init__(self, spawner, arango_root_password):
        self.arango_root_password = arango_root_password
        self.spawner = spawner

    async def deploy_agent(self, name, language="en", skills=[]):
        wait = False

        if not await self.spawner.exist_service(name):
            client = MatrixClient("http://matrix")
            password = ''.join(random.choice(string.ascii_lowercase) for i in range(20))

            try:
                token = client.register_with_password(username=name, password=password)

                _LOGGER.info("Creating bot in matrix - token = " + token)
            except MatrixRequestError:
                _LOGGER.info("Error creating bot in matrix ")

            if name == 'abot':
                try:
                    client.create_room(name="bots", invitees="@" + name + ":local")
                    _LOGGER.info("Creating room bots")
                except MatrixRequestError:
                    _LOGGER.info("Error creating room bots")

            _LOGGER.info("Deploying agent " + name)
            config = {"services": [{"name": 'agent',
                                    "agent-name": name,
                                    "skills": skills}],
                      "databases": [],
                      "connectors": [{"name": "mqtt"},
                                     {"name": "matrix",
                                      "nick": name,
                                      "mxid": "@" + name + ":local",
                                      "password": password,
                                      "room": "@bots:local",
                                      "homeserver": "http://matrix:8008"}]}
            await Platform.create_service_config(name, config)

            await self.spawner.deploy_service(name,
                                              "eternius/arcusservice:latest",
                                              None,
                                              {"ARCUS_SERVICE": name},
                                              {"conf:" + name + ".yml": "/opt/arcus/conf/config.yml"},
                                              {})
        else:
            container = await self.spawner.get_container(name)
            if container.status != "running":
                _LOGGER.info("Starting agent " + name)
                container.start()

        skill_manager = Skill(self.spawner, self.arango_root_password)
        for skill in skills:
            await skill_manager.deploy_skill(skill, language)

        if wait:
            _LOGGER.info("Waiting for services to start")
            await asyncio.sleep(20)
