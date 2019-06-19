import random
import openpyxl
import nltk
from nltk.stem.lancaster import LancasterStemmer

from rasa.nlu.training_data import Message
from pattern.text.en import suggest as suggest_en
from pattern.text.es import suggest as suggest_es

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


class GenerateStories:
    @staticmethod
    async def run(memory, language):
        intents_number = 0
        data = []
        stories = []
        intent_stories = []
        domain_data = {"intents": [],
                       "actions": [],
                       "templates": {},
                       "config": {},
                       "entities": [],
                       "slots": {},
                       "forms": []}

        bot_document = openpyxl.load_workbook('./bot-data/bot.xlsx')
        sheet = bot_document.get_sheet_by_name('intents')

        intent_id = ""
        all_rows = sheet.rows
        for row in all_rows:
            if row[INTENT_NAME].value != "intent":
                if row[INTENT_NAME].value is not None:
                    intent_id = row[INTENT_NAME].value
                    intents_number += 1

                    if row[INTENT_DIALOG].value is None and row[INTENT_DEFAULT_RESPONSE].value is not None:
                        i = {intent_id: {"use_entities": False, "triggers": 'utter_' +intent_id}}
                    else:
                        i = {intent_id: {"use_entities": False}}

                    domain_data['intents'].append(i)
                    if row[INTENT_DEFAULT_RESPONSE].value is not None:
                        domain_data['actions'].append('utter_' + intent_id)
                        stories.append('## ' + intent_id)

                        intent_story = []
                        if row[INTENT_DIALOG].value is not None:
                            domain_data['forms'].append(intent_id + '_form')
                            domain_data['slots']['requested_slot'] = {"type": "unfeaturized"}
                            slot = bot_document.get_sheet_by_name(row[INTENT_DIALOG].value)
                            slot_def = []
                            for slot_item in slot.rows:
                                if slot_item[SLOT_NAME].value != "name":
                                    domain_data['slots'][slot_item[SLOT_NAME].value] = {"type": "unfeaturized", "auto_fill": False}
                                    domain_data['templates']['utter_ask_' + slot_item[SLOT_NAME].value] = \
                                        [{"text": slot_item[SLOT_QUESTION].value}]
                                    domain_data['templates']['utter_error_' + slot_item[SLOT_NAME].value] = \
                                        [{"text": slot_item[SLOT_RESPONSE_ERROR].value}]
                                    domain_data['entities'].append(slot_item[SLOT_NAME].value)
                                    slot_def.append({"name": slot_item[SLOT_NAME].value,
                                                     "required": slot_item[SLOT_REQUIRED].value,
                                                     "type": slot_item[SLOT_TYPE].value,
                                                     "validation_function": slot_item[SLOT_VALIDATE_FUNCTION].value})

                            await memory.put(intent_id, {"function": row[INTENT_FUNCTION].value, "slot": slot_def})
                            for y in range(5):
                                intent_story.append('* ' + intent_id)
                                intent_story.append('  - ' + intent_id + '_form')
                                intent_story.append('  - form{"name": "' + intent_id + '_form"}')
                                intent_story.append('  - form{"name": null}')
                                intent_story.append('  - utter_' + intent_id)
                        else:
                            """ intent_story.append('* ' + intent_id)
                            intent_story.append('  - utter_' + intent_id)"""

                        intent_stories.append(intent_story)
                        for item in intent_story:
                            stories.append(item)

                if row[INTENT_EXAMPLES].value is not None:
                    text = GenerateStories.preprocessor(row[INTENT_EXAMPLES].value, language)
                    msg = Message.build(text=text, intent=intent_id)
                    data.append(msg)

                if row[INTENT_DEFAULT_RESPONSE].value is not None:
                    domain_data['templates']['utter_' + intent_id] = [{"text": row[INTENT_DEFAULT_RESPONSE].value}]

        for x in range(intents_number * 20):
            stories.append('## random_' + str(x))
            for y in range(5):
                story = random.choice(intent_stories)
                for item in story:
                    stories.append(item)

        return data, domain_data, stories

    @staticmethod
    def preprocessor(message_text, language):
        ignore_words = ['?', '¿', '¡', '!', '.', ',', ':']

        words = nltk.word_tokenize(message_text.strip())

        if language == 'en':
            for idx, val in enumerate(words):
                try:
                    s = suggest_en(val)
                    if s[0][1] > 0.7:
                        words[idx] = s[0][0]
                except:
                    continue
        elif language == 'es':
            for idx, val in enumerate(words):
                try:
                    s = suggest_es(val)
                    if s[0][1] > 0.7:
                        words[idx] = s[0][0]
                except:
                    continue

        stemmer = LancasterStemmer()
        text = [stemmer.stem(w.lower()) for w in words if w not in ignore_words]

        return " ".join(str(x) for x in text)
