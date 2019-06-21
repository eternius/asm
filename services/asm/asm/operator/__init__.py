import os
import logging

from asm.operator.platform import Platform
from asm.operator.agent import Agent
from asm.utils.spawners.dockerspawner import DockerSpawner

_LOGGER = logging.getLogger(__name__)


class Operator:
    def __init__(self, arango_root_password):
        if os.path.exists("/var/run/docker.sock"):
            spawner = DockerSpawner()

        self.platform = Platform(spawner, arango_root_password)
        self.agent = Agent(spawner, arango_root_password)
