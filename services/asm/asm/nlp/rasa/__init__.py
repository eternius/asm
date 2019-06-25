import os
import logging
import nltk

from asm.nlp import NLP
from asm.nlp.rasa.arcus_tracker_store import ArcusTrackerStore
from asm.nlp.rasa.generate_stories import GenerateStories
from asm.nlp.rasa.local_nlu_interpreter import LocalNLUInterpreter
from asm.nlp.rasa.generic_form_action import GenericFormAction
from rasa.nlu.training_data import TrainingData
from rasa.nlu.model import Interpreter, Trainer
from rasa.nlu.config import RasaNLUModelConfig
from rasa.core.policies import SimplePolicyEnsemble
from rasa.core.domain import Domain
from rasa.core.interpreter import RegexInterpreter
from rasa.core.training.structures import StoryGraph
from rasa.core.training.generator import TrainingDataGenerator
from rasa.core.training.dsl import StoryFileReader
from rasa.utils.endpoints import EndpointConfig
from rasa.core.nlg import NaturalLanguageGenerator
from rasa.core.processor import MessageProcessor
from rasa.core.channels import UserMessage
from rasa_sdk.interfaces import Tracker
from rasa_sdk.executor import CollectingDispatcher

from asm.utils.matchers import match_nlp_train, match_parse_text, match_get_response, match_generic_action

_LOGGER = logging.getLogger(__name__)


class Rasa(NLP):
    @match_nlp_train()
    async def train(self):
        """Train the engine.
        """
        nltk.download('punkt')
        lang = self.config['language']
        if not os.path.exists('data/' + self.config['skill-id']):
            _LOGGER.info("Starting Skill training.")
            _LOGGER.info("Generating stories.")
            data, domain_data, stories = await GenerateStories.run(self.config['skill-id'],
                                                                   self.config['language'],
                                                                   self.asm)
            training_data = TrainingData(training_examples=data)
            nlu_config = RasaNLUModelConfig({"language": lang,
                                             "pipeline": self.config['pipeline'],
                                             "data": None})

            trainer = Trainer(nlu_config, None, True)
            _LOGGER.info("Training Rasa NLU")
            trainer.train(training_data)
            trainer.persist("data/" + self.config['skill-id'], None, 'nlu')

            # Rasa core
            domain = Domain.from_dict(domain_data)

            reader = StoryFileReader(domain, RegexInterpreter(), None, False)
            story_steps = await reader.process_lines(stories)
            graph = StoryGraph(story_steps)

            g = TrainingDataGenerator(
                graph,
                domain,
                remove_duplicates=True,
                unique_last_num_states=None,
                augmentation_factor=20,
                tracker_limit=None,
                use_story_concatenation=True,
                debug_plots=False,
            )

            training_trackers = g.generate()
            policy_list = SimplePolicyEnsemble.from_dict({"policies": self.config['policies']})
            policy_ensemble = SimplePolicyEnsemble(policy_list)

            _LOGGER.info("Training Rasa Core")
            policy_ensemble.train(training_trackers, domain)
            policy_ensemble.persist("data/" + self.config['skill-id'] + "/core", False)
            domain.persist("data/" + self.config['skill-id'] + "/core/model")
            domain.persist_specification("data/" + self.config['skill-id'] + "/core")

    @match_parse_text()
    async def parse_text(self, text):
        """Train the engine.
        """
        text = GenerateStories.preprocessor(text, self.config["language"])

        if self.config.get('interpreter') is None:
            self.config.setdefault('interpreter',
                                   Interpreter.load("data/" + self.config['skill-id'] + "/nlu",
                                                    None))

        interpreter = self.config.get('interpreter')
        return interpreter.parse(text)

    @match_get_response()
    async def get_response(self, request):
        """Train the engine.
        """
        if self.config.get('domain') is None:
            self.config.setdefault('domain', Domain.from_file("data/" + self.config['skill-id'] + "/core/model"))
            self.config.setdefault('tracker_store', ArcusTrackerStore(self.config.get('domain'),
                                                                      self.asm))

        domain = self.config.get('domain')
        tracker_store = self.config.get('tracker_store')
        nlg = NaturalLanguageGenerator.create(None, domain)
        policy_ensemble = SimplePolicyEnsemble.load("data/" + self.config['skill-id'] + "/core")
        interpreter = LocalNLUInterpreter(request)

        url = 'http://localhost:8080/api/v1/skill/generic_action'
        processor = MessageProcessor(interpreter,
                                     policy_ensemble,
                                     domain,
                                     tracker_store,
                                     nlg,
                                     action_endpoint=EndpointConfig(url),
                                     message_preprocessor=None)

        message_nlu = UserMessage(request['text'], None, request['user'], input_channel=request['channel'])

        result = await processor.handle_message(message_nlu)
        if result is not None and len(result) > 0:
            return {"text": result[0]['text']}
        else:
            _LOGGER.info(result)
            return {"text": "error"}

    @match_generic_action()
    async def generic_action(self, request):
        action_name = request.get("next_action")
        if action_name:
            _LOGGER.debug("Received request to run '{}'".format(action_name))

            tracker_json = request.get("tracker")
            domain = request.get("domain", {})
            tracker = Tracker.from_dict(tracker_json)
            dispatcher = CollectingDispatcher()

            if action_name.endswith("_form"):
                intent_id = action_name[:-5]
                intent = await self.asm.memory.get(self.config['skill-id'] + "_intents", intent_id)
                gfa = GenericFormAction()
                gfa.set_name(action_name)
                gfa.set_intent(intent)
                gfa.set_domain(domain)
                gfa.set_memory(self.asm.memory)
                events = gfa.run(dispatcher, tracker, domain)

            if not events:
                # make sure the action did not just return `None`...
                events = []

            validated_events = self.validate_events(events, action_name)
            _LOGGER.debug("Finished running '{}'".format(action_name))
        else:
            _LOGGER.warning("Received an action call without an action.")

        return {"events": validated_events, "responses": dispatcher.messages}

    @staticmethod
    def validate_events(events, action_name):
        validated = []
        for e in events:
            if isinstance(e, dict):
                if not e.get("event"):
                    _LOGGER.error(
                        "Your action '{}' returned an action dict "
                        "without the `event` property. Please use "
                        "the helpers in `rasa_sdk.events`! Event will"
                        "be ignored! Event: {}".format(action_name, e)
                    )
                else:
                    validated.append(e)
            elif type(e).__module__ == "rasa.core.events":
                _LOGGER.warning(
                    "Your action should not return Rasa actions within the "
                    "SDK. Instead of using events from "
                    "`rasa.core.events`, you should use the ones "
                    "provided in `rasa_sdk.events`! "
                    "We will try to make this work, but this "
                    "might go wrong!"
                )
                validated.append(e.as_dict())
            else:
                _LOGGER.warning(
                    "Your action's '{}' run method returned an invalid "
                    "event. Event will be ignored. "
                    "Event: '{}'.".format(action_name, e)
                )
                # we won't append this to validated events -> will be ignored
        return validated
