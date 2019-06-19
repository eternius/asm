import os
import yaml
import logging
import asyncio

from asm.utils.dockerspawner import DockerSpawner
from minio import Minio
from minio.error import (ResponseError, BucketAlreadyOwnedByYou,
                         BucketAlreadyExists)

_LOGGER = logging.getLogger(__name__)


class Operator:
    def __init__(self):
        self.access_key = os.getenv('MINIO_ACCESS_KEY', "arcusarcus")
        self.secret_key = os.getenv('MINIO_SECRET_KEY', "arcusarcus")

        self.minio_client = Minio('minio:9000',
                                  access_key=self.access_key,
                                  secret_key=self.secret_key,
                                  secure=False)

    async def check_core_platform(self):
        with open("conf/core-services.yaml", 'r') as stream:
            try:
                core_services = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                _LOGGER.error("Error loading config.yaml.", exc)
                core_services = {"external-services": []}

            if os.path.exists("/var/run/docker.sock"):
                spawner = DockerSpawner()

            wait = False
            for service in core_services['external-services']:
                if not await spawner.exist_service(service['name']):
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
                            volumes[volume['src']] = {'bind': volume['dst'], 'mode': volume['mode']}

                    ports = {}
                    if 'ports' in service:
                        for port in service['ports']:
                            for key, value in port.items():
                                ports[str(key) + '/tcp'] = int(value)

                    await spawner.deploy_service(service['name'],
                                                 service['image'],
                                                 service['command'],
                                                 env,
                                                 volumes,
                                                 ports)

                    wait = True

            if wait:
                _LOGGER.info("Waiting for services to start")
                await asyncio.sleep(20)

                config = {"services": [{"name": "operator"}],
                          "databases": [],
                          "connectors": [{"name": "mqtt"}]}
                await self.create_service_config("operator", config)

            for agent in core_services['agents']:
                skills = []
                for skill in agent['skills']:
                    skills.append(skill)

                await self.deploy_agent(agent['name'], agent['language'], skills, spawner)

    async def create_service_config(self, name, data):
        try:
            self.minio_client.make_bucket("services-" + name, location="us-east-1")
        except BucketAlreadyOwnedByYou as err:
            pass
        except BucketAlreadyExists as err:
            pass
        except ResponseError as err:
            raise
        else:
            with open('config.yml', 'w') as outfile:
                yaml.dump(data, outfile, default_flow_style=False)
            try:
                self.minio_client.fput_object('services-' + name, 'config.yml', 'config.yml')
            except ResponseError as err:
                _LOGGER.error(err)

    async def deploy_agent(self, name, language="en", skills=[], spawner=None):
        config = {"services": [{"name": name,
                                "skills": skills}],
                  "databases": [],
                  "connectors": [{"name": "mqtt"},
                                 {"name": "websocket", "bot-name": name}]}
        await self.create_service_config(name, config)

        await spawner.deploy_service(name,
                                     "eternius/arcusservice:latest",
                                     None,
                                     {"ARCUS_SERVICE": name,
                                      "MINIO_ACCESS_KEY": self.access_key,
                                      "MINIO_SECRET_KEY": self.secret_key},
                                     {},
                                     {})

        for skill in skills:
            # Create NLP Skill service configuration
            config = {"services": [{"name": "nlp",
                                    "skill-id": skill,
                                    "language": language}],
                      "databases": [],
                      "connectors": [{"name": "mqtt"}]}
            await self.create_service_config("skill-" + skill + "-nlp", config)

            await spawner.deploy_service("skill-" + skill + "-nlp",
                                         "eternius/arcusservice:latest",
                                         None,
                                         {"ARCUS_SERVICE": "skill-" + skill + "-nlp",
                                          "MINIO_ACCESS_KEY": self.access_key,
                                          "MINIO_SECRET_KEY": self.secret_key},
                                         {},
                                         {})

            # Create Core Skill service configuration
            config = {"services": [{"name": "core",
                                    "skill-id": skill,
                                    "policies": [
                                        {"name": "MappingPolicy"},
                                        {"name": "FormPolicy"},
                                        {"name": "MemoizationPolicy"},
                                        {"name": "FallbackPolicy"}
                                    ],
                                    "language": language}],
                      "databases": [],
                      "connectors": [{"name": "mqtt"}]}
            await self.create_service_config("skill-" + skill + "-core", config)

            await spawner.deploy_service("skill-" + skill + "-core",
                                         "eternius/arcusservice:latest",
                                         None,
                                         {"ARCUS_SERVICE": "skill-" + skill + "-core",
                                          "MINIO_ACCESS_KEY": self.access_key,
                                          "MINIO_SECRET_KEY": self.secret_key},
                                         {},
                                         {})
