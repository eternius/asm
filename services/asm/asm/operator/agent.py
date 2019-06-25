import logging
import asyncio

from asm.operator.platform import Platform
from asm.operator.skill import Skill

_LOGGER = logging.getLogger(__name__)


class Agent:
    def __init__(self, spawner, arango_root_password):
        self.arango_root_password = arango_root_password
        self.spawner = spawner

    async def deploy_agent(self, name, language="en", skills=[]):
        wait = False

        if not await self.spawner.exist_service(name):
            _LOGGER.info("Deploying agent " + name)
            config = {"services": [{"name": 'agent',
                                    "agent-name": name,
                                    "skills": skills}],
                      "databases": [],
                      "connectors": [{"name": "slack",
                                      "api-token": "xoxb-101051548259-668871292337-5brywD6tOvvI7bjsJOxLVae7",
                                      "bot-name": "abot",
                                      "default-room": "#general",
                                      "icon-emoji": ":robot_face:"}]}
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
