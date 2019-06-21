import requests
import os
import logging
import re
import random

from typing import Dict, Text, Any, List, Union
from rasa_sdk import Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormAction
from rasa_sdk.events import SlotSet
import importlib
import importlib.util
from asm.utils.loader import Loader
from asm.utils.function.context import Context
from asm.utils.function.event import Event
from asm.utils.function.logger import Logger


class GenericFormAction(FormAction):
    """Example of a custom form action"""
    form_name = "GenericFormAction"
    intent = {}
    intent_id = ""
    memory = None
    domain = None

    def set_name(self, name):
        self.form_name = name

    def set_intent(self, intent):
        self.intent = intent

    def set_memory(self, memory):
        self.memory = memory

    def set_domain(self, domain):
        self.domain = domain

    def name(self):
        # type: () -> Text
        """Unique identifier of the form"""

        return self.form_name

    def required_slots(self, tracker: Tracker) -> List[Text]:
        """A list of required slots that the form has to fill"""

        required = []
        for slot_item in self.intent['slot'] :
            if slot_item['required'] == 'Y':
                required.append(slot_item['name'])

        return required

    def slot_mappings(self):
        # type: () -> Dict[Text: Union[Dict, List[Dict]]]
        """A dictionary to map required slots to
            - an extracted entity
            - intent: value pairs
            - a whole message
            or a list of them, where a first match will be picked"""

        slot_mappings = {}

        for slot_item in self.intent['slot']:
            if slot_item['required'] == 'Y':
                slot_mappings[slot_item['name']] = [self.from_entity(entity=slot_item['name']),
                                                    self.from_text()]

        return slot_mappings

    def submit(self,
               dispatcher: CollectingDispatcher,
               tracker: Tracker,
               domain: Dict[Text, Any]) -> List[Dict]:
        """Define what the form has to do
            after all required slots are filled"""

        result = {}
        data = {}
        slots = []

        if 'function' in self.intent:
            function = self.intent['function']

            for key, value in tracker.slots.items():
                slots.append(SlotSet(key, None))
                if type(value) is dict:
                    data[key] = value['text']
                else:
                    data[key] = value
            data['abot.user_id'] = tracker.sender_id
            result = self.call_function(function, data)

        # utter submit template
        for key, value in result.items():
            data[key] = value

        resp = random.choice(domain['templates']["utter_" + self.form_name[:-5]])['text']
        text = re.sub(r"@([^\n]+?)@", r"{0[\1]}", resp)
        result = text.format(data)

        dispatcher.utter_message(result)
        return slots

    def validate_slots(self, slot_dict, dispatcher, tracker, domain):
        for slot, value in list(slot_dict.items()):
            field = {}
            validation_output = {}

            for item in self.intent['slot']:
                if item['name'] == slot:
                    field = item
                    break

            if len(field) > 0:
                valid_values = []
                if field['type'] is not None and field['type'].startswith('['):
                    valid_values = field['type'][1:-1].split(",")
                    valid_values = [item.strip() for item in valid_values]

                if field['type'] is not None:
                    data = {'locale': 'es_ES', 'text': value}
                    res = requests.post("http://duckling:8000/parse",
                                        data=data)
                    result = res.json()

                    if field['type'] == 'number':
                        try:
                            value = int(value)
                            validation_output = {slot: value}
                        except ValueError:
                            validation_output = {}
                    elif field['type'] == 'date':
                        if len(result) > 0 and 'dim' in result[0] and result[0]['dim'] == 'time':
                            value = result[0]['value']['value'][:10]
                            validation_output = {slot: value}
                    elif tracker.latest_message['intent']['name'] is not None and \
                            tracker.latest_message['intent']['confidence'] > 0.6 and \
                            '@' + tracker.latest_message['intent']['name'] in valid_values:
                        validation_output = {slot: '@' + tracker.latest_message['intent']['name']}
                elif field['validation_function'] is not None:
                    result = self.call_function(field['validation_function'], {"value": value})
                    if result['valid']:
                        validation_output = {slot: result['value']}

                if len(validation_output) == 0:
                    if tracker.latest_message['intent']['name'] is not None and \
                            tracker.latest_message['intent']['confidence'] > 0.6:
                        # Respond question in slot
                        resp = random.choice(domain['templates']
                                             ["utter_" + tracker.latest_message['intent']['name']])['text']
                        resp = resp + '. ' + random.choice(domain['templates']
                                                           ["utter_error_" + field['name']])['text']
                    else:
                        resp = random.choice(domain['templates']["utter_error_" + field['name']])['text']

                    dispatcher.utter_message(resp)
                    slot_dict.pop(item['name'])
                else:
                    slot_dict.update(validation_output)

        # validation succeed, set slots to extracted values
        return [SlotSet(slot, value) for slot, value in slot_dict.items()]

    def call_function(self, function_name, data):
        faas = os.getenv("FAAS_URL", "")
        result = {}

        if faas == "":
            """ Local function """
            module_spec = None

            try:
                module_spec = importlib.util.find_spec("abot.function." + function_name)
            except (ImportError, AttributeError):
                print("Error loading function " + function_name)

            if module_spec:
                module = Loader.import_module_from_spec(module_spec)

                context = Context(Logger(logging.DEBUG), self.memory)
                event = Event(data)
                result = module.handler(context, event)
        else:
            """ Remote function """
            data['function'] = function_name
            res = requests.post(faas,
                                json=data)
            result = res.json()

        return result
