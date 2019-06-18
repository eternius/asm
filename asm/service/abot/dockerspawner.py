import logging
import docker

from asm.service.abot.spawner import Spawner
from docker.errors import NotFound, ImageNotFound, APIError

_LOGGER = logging.getLogger(__name__)


class DockerSpawner(Spawner):
    def __init__(self, *args, **kwargs):
        self.client = docker.from_env()

    async def exist_service(self, service_name):
        try:
            self.client.containers.get(service_name)
            return True
        except NotFound:
            return False

    async def deploy_service(self, service_name, image, env={}, volumes={}, ports={}):
        try:
            self.client.containers.run(name=service_name,
                                       image=image,
                                       environment=env,
                                       volumes=volumes,
                                       ports=ports,
                                       detach=True)
            return True
        except NotFound or ImageNotFound or APIError:
            _LOGGER.erro("Error deploying service %s", service_name)
            return False

    async def get_secret(self, name):
        try:
            return self.client.secrets.get(name).attrs
        except NotFound or APIError:
            return None

    async def create_secret(self, name, data):
        return self.client.secrets.create(name, bytes(data))
