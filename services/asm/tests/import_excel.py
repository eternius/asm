import os
import asyncio
import openpyxl

from asm.database.mongo import DatabaseMongo

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


async def main():
    name = 'abot'

    if os.path.exists('data/' + name + '.xlsx'):
        # Connect to DB
        db = DatabaseMongo({"host": "127.0.0.1", "port": 27017, "database": "admin"})
        await db.connect()

        # Import skill definition
        bot_document = openpyxl.load_workbook('data/' + name + '.xlsx')
        sheet = bot_document['intents']

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
                    slot = bot_document[row[INTENT_DIALOG].value]

                    for slot_item in slot.rows:
                        if slot_item[SLOT_NAME].value != "name":
                            slot_def = {"name": slot_item[SLOT_NAME].value,
                                        "required": slot_item[SLOT_REQUIRED].value,
                                        "type": slot_item[SLOT_TYPE].value,
                                        "validation_function": slot_item[SLOT_VALIDATE_FUNCTION].value,
                                        "question": slot_item[SLOT_QUESTION].value,
                                        "response_error": slot_item[SLOT_RESPONSE_ERROR].value}
                            intent['slot'].append(slot_def)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
