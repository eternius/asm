import os
import logging
import yaml
import asyncio

_LOGGER = logging.getLogger(__name__)


class Platform:
    def __init__(self, spawner, arango_root_password):
        self.arango_root_password = arango_root_password
        self.spawner = spawner

    async def deploy_core_platform(self):
        with open("conf/core-services.yaml", 'r') as stream:
            try:
                core_services = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                _LOGGER.error("Error loading config.yaml.", exc)
                core_services = {"external-services": []}

            wait = False
            for service in core_services['external-services']:
                if not await self.spawner.exist_service(service['name']):
                    _LOGGER.info("Deploying " + service['name'])
                    envvars = {}
                    for envvar in service['envvars']:
                        for key, value in envvar.items():
                            envvars[key] = os.getenv(key, value)

                    env = {}
                    for var in service['env']:
                        for key, value in var.items():
                            if value.startswith('envvar'):
                                env[key] = envvars[value[7:]]
                            else:
                                env[key] = value

                    if 'command' not in service:
                        service['command'] = None

                    volumes = {}
                    if 'volumes' in service:
                        for volume in service['volumes']:
                            volumes[volume['src']] = volume['dst']

                    ports = {}
                    if 'ports' in service:
                        for port in service['ports']:
                            for key, value in port.items():
                                ports[str(key) + '/tcp'] = int(value)

                    await self.spawner.deploy_service(service['name'],
                                                 service['image'],
                                                 service['command'],
                                                 env,
                                                 volumes,
                                                 ports)

                    wait = True
                else:
                    container = await self.spawner.get_container(service['name'])
                    if container.status != "running":
                        container.start()
                        wait = True

            if wait:
                _LOGGER.info("Waiting for services to start")
                await asyncio.sleep(20)

                # Create config.yml for operator
                config = {"services": [{"name": "operator"}],
                          "databases": [{"name": "arangodb",
                                         "password": self.arango_root_password}],
                          "connectors": [{"name": "mqtt"}]}
                await Platform.create_service_config("operator", config)

    @staticmethod
    async def create_service_config(name, data):
        with open('/opt/arcus/conf/' + name + '.yml', 'w') as outfile:
            yaml.dump(data, outfile, default_flow_style=False)
