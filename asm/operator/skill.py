import os
import logging
import openpyxl

from asm.operator.platform import Platform
from asm.database.arangodb import DatabaseArangoDB

# Excel cols
INTENT_NAME = 0
INTENT_EXAMPLES = 1
INTENT_DIALOG = 2
INTENT_FUNCTION = 3
INTENT_DEFAULT_RESPONSE = 4

SLOT_NAME = 0
SLOT_REQUIRED = 1
SLOT_TYPE = 2
SLOT_VALIDATE_FUNCTION = 3
SLOT_QUESTION = 4
SLOT_RESPONSE_ERROR = 5

_LOGGER = logging.getLogger(__name__)


class Skill:
    def __init__(self, spawner, arango_root_password):
        self.arango_root_password = arango_root_password
        self.spawner = spawner

    async def deploy_skill(self, name, language="en"):
        if not await self.spawner.exist_service("skill-" + name):
            if os.path.exists('data/' + name + '.xlsx'):
                # Connect to DB
                db = DatabaseArangoDB({"password": self.arango_root_password})
                await db.connect()

                # Import skill definition
                bot_document = openpyxl.load_workbook('data/' + name + '.xlsx')
                sheet = bot_document.get_sheet_by_name('intents')

                intent_id = ""
                all_rows = sheet.rows
                for row in all_rows:
                    if row[INTENT_NAME].value != "intent":
                        if row[INTENT_NAME].value is not None:
                            if intent_id is not "":
                                await db.put(name + "_intents", intent_id, intent)
                            intent_id = row[INTENT_NAME].value

                            intent = {"examples": [],
                                      "function": None,
                                      "slot": [],
                                      "responses": {}}

                        if row[INTENT_EXAMPLES].value is not None:
                            intent['examples'].append(row[INTENT_EXAMPLES].value)

                        if row[INTENT_FUNCTION].value is not None:
                            intent['function'] = row[INTENT_FUNCTION].value

                        if row[INTENT_DEFAULT_RESPONSE].value is not None:
                            if 'default' not in intent['responses']:
                                intent['responses']['default'] = []
                            intent['responses']['default'].append(row[INTENT_DEFAULT_RESPONSE].value)

                        if row[INTENT_DIALOG].value is not None:
                            slot = bot_document.get_sheet_by_name(row[INTENT_DIALOG].value)

                            for slot_item in slot.rows:
                                if slot_item[SLOT_NAME].value != "name":
                                    slot_def = {"name": slot_item[SLOT_NAME].value,
                                                "required": slot_item[SLOT_REQUIRED].value,
                                                "type": slot_item[SLOT_TYPE].value,
                                                "validation_function": slot_item[SLOT_VALIDATE_FUNCTION].value,
                                                "question": slot_item[SLOT_QUESTION].value,
                                                "response_error": slot_item[SLOT_RESPONSE_ERROR].value}
                                    intent['slot'].append(slot_def)

            # Create Skill service configuration
            _LOGGER.info("Deploying skill " + name)
            config = {"services": [{"name": "skill",
                                    "skill-id": name,
                                    "language": language}],
                      "databases": [{"name": "arangodb",
                                     "password": self.arango_root_password}],
                      "connectors": [{"name": "mqtt"}]}
            await Platform.create_service_config("skill-" + name, config)

            await self.spawner.deploy_service("skill-" + name,
                                              "eternius/arcusservice:latest",
                                              None,
                                              {"ARCUS_SERVICE": "skill-" + name},
                                              {"conf:skill-" + name + ".yml": "/opt/arcus/conf/config.yml"},
                                              {})
        else:
            container = await self.spawner.get_container("skill-" + name)
            if container.status != "running":
                _LOGGER.info("Starting skill " + name)
                container.start()
