import random
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
    async def run(skill, language, asm):
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

        intents = await asm.memory.get_keys(skill + "_intents")

        for intent_id in intents:
            intent = await asm.memory.get(skill + "_intents", intent_id)

            if len(intent['slot']) == 0:
                i = {intent_id: {"use_entities": False, "triggers": 'utter_' + intent_id}}
            else:
                i = {intent_id: {"use_entities": False}}

            domain_data['intents'].append(i)
            domain_data['actions'].append('utter_' + intent_id)
            stories.append('## ' + intent_id)

            domain_data['templates']['utter_' + intent_id] = []
            if intent['responses'] is not None and 'default' in intent['responses']:
                for response in intent['responses']['default']:
                    domain_data['templates']['utter_' + intent_id].append({"text": response})

            for example in intent['examples']:
                text = GenerateStories.preprocessor(example, language)
                msg = Message.build(text=text, intent=intent_id)
                data.append(msg)

            if len(intent['slot']) > 0:
                intent_story = []
                domain_data['forms'].append(intent_id + '_form')
                domain_data['slots']['requested_slot'] = {"type": "unfeaturized"}
                slot_def = []
                for slot_item in intent['slot']:
                    domain_data['slots'][slot_item['name']] = {"type": "unfeaturized", "auto_fill": False}
                    domain_data['templates']['utter_ask_' + slot_item['name']] = \
                        [{"text": slot_item['question']}]
                    domain_data['templates']['utter_error_' + slot_item['name']] = \
                        [{"text": slot_item['response_error']}]
                    domain_data['entities'].append(slot_item['name'])
                    slot_def.append({"name": slot_item['name'],
                                     "required": slot_item['required'],
                                     "type": slot_item['type'],
                                     "validation_function": slot_item['validation_function']})
                for y in range(5):
                    intent_story.append('* ' + intent_id)
                    intent_story.append('  - ' + intent_id + '_form')
                    intent_story.append('  - form{"name": "' + intent_id + '_form"}')
                    intent_story.append('  - form{"name": null}')
                    intent_story.append('  - utter_' + intent_id)

                intent_stories.append(intent_story)
                for item in intent_story:
                    stories.append(item)

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
