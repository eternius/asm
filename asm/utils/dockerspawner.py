import logging
import docker

from asm.utils.spawner import Spawner
from docker.errors import NotFound, ImageNotFound, APIError

_LOGGER = logging.getLogger(__name__)


class DockerSpawner(Spawner):
    def __init__(self, *args, **kwargs):
        self.client = docker.from_env()

        networks = self.client.networks.list()
        create = True

        for network in networks:
            if network.name == "arcus":
                create = False
                break

        if create:
            self.client.networks.create("arcus")

    async def exist_service(self, service_name):
        try:
            self.client.containers.get(service_name)
            return True
        except NotFound:
            return False

    async def deploy_service(self, service_name, image, command, env={}, volumes={}, ports={}):
        try:
            if await self.exist_service(service_name):
                container = await self.get_container(service_name)
                if container.status != "running":
                    container.start()

                return True

            if command is None:
                self.client.containers.run(name=service_name,
                                           image=image,
                                           environment=env,
                                           volumes=volumes,
                                           ports=ports,
                                           network="arcus",
                                           detach=True)
            else:
                self.client.containers.run(name=service_name,
                                           image=image,
                                           command=command,
                                           environment=env,
                                           volumes=volumes,
                                           network="arcus",
                                           ports=ports,
                                           detach=True)
            return True
        except NotFound or ImageNotFound or APIError:
            _LOGGER.error("Error deploying service %s", service_name)
            return False

    async def get_secret(self, name):
        try:
            return self.client.secrets.get(name).attrs
        except NotFound or APIError:
            return None

    async def create_secret(self, name, data):
        return self.client.secrets.create(name, bytes(data))

    async def get_container(self, name):
        return self.client.containers.get(name)
