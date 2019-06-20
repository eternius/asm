import os
import logging
import asyncio
import nltk

from asm.service import Service
from asm.utils.matchers import match_service
from asm.service.skill.generate_stories import GenerateStories
from rasa.nlu.training_data import TrainingData
from rasa.nlu.model import Interpreter, Trainer
from rasa.nlu.config import RasaNLUModelConfig
from rasa.core.policies import SimplePolicyEnsemble
from rasa.core.domain import Domain
from rasa.core.interpreter import RegexInterpreter
from rasa.core.training.structures import StoryGraph
from rasa.core.training.generator import TrainingDataGenerator
from rasa.core.training.dsl import StoryFileReader

_LOGGER = logging.getLogger(__name__)


class Skill(Service):
    async def setup(self):
        nltk.download('punkt')
        lang = self.config['language']
        if not os.path.exists('data/' + self.config['skill-id']):
            _LOGGER.info("Starting Skill training.")
            _LOGGER.info("Generating stories.")
            data, domain_data, stories = await GenerateStories.run(self.config['skill-id'],
                                                                   self.config['language'],
                                                                   self.asm)
            training_data = TrainingData(training_examples=data)

            pipeline = [
                {"name": "WhitespaceTokenizer"},
                {"name": "CRFEntityExtractor"},
                {"name": "EntitySynonymMapper"},
                {"name": "CountVectorsFeaturizer", "token_pattern": '(?u)\\b\w+\\b'},
                {"name": "EmbeddingIntentClassifier"}
            ]

            nlu_config = RasaNLUModelConfig({"language": lang,
                                             "pipeline": pipeline,
                                             "data": None})

            trainer = Trainer(nlu_config, None, True)
            _LOGGER.info("Training NLU")
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

            policies = [
                {"name": "MappingPolicy"},
                {"name": "FormPolicy"},
                {"name": "MemoizationPolicy"},
                {"name": "FallbackPolicy"}
            ]

            policy_list = SimplePolicyEnsemble.from_dict({"policies": policies})
            policy_ensemble = SimplePolicyEnsemble(policy_list)

            _LOGGER.info("Training Core")
            policy_ensemble.train(training_trackers, domain)
            policy_ensemble.persist("data/" + self.config['skill-id'] + "/core", False)
            domain.persist("data/" + self.config['skill-id'] + "/core/model")
            domain.persist_specification("data/" + self.config['skill-id'] + "/core")

    @match_service('')
    async def parse(self, asm, services, message, config):
        text = GenerateStories.preprocessor(message.text, config["language"])

        if asm.config.get('interpreter') is None:
            asm.config.setdefault('interpreter',
                                  Interpreter.load("data/model/" + self.config['skill-id'],
                                                   None))

        interpreter = asm.config.get('interpreter')
        result = interpreter.parse(text)
