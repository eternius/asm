import os


class Agent:
    def __init__(self, arango_root_password):
        self.arango_root_password = arango_root_password

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
                                     {"ARCUS_SERVICE": name},
                                     {"conf:" + name + ".yml": "/opt/arcus/conf/config.yml"},
                                     {})

        for skill in skills:
            # Create Skill service configuration
            config = {"services": [{"name": "skill",
                                    "skill-id": skill,
                                    "language": language}],
                      "databases": [{"name": "arangodb",
                                     "password": self.arango_root_password}],
                      "connectors": [{"name": "mqtt"}]}
            await self.create_service_config("skill-" + skill, config)

            await spawner.deploy_service("skill-" + skill,
                                         "eternius/arcusservice:latest",
                                         None,
                                         {"ARCUS_SERVICE": "skill-" + skill},
                                         {"conf:skill-" + skill + ".yml": "/opt/arcus/conf/config.yml"},
                                         {})
