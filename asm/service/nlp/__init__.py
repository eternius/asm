import os
import logging

from asm.service import Service
from asm.utils.matchers import match_service
from asm.utils.nlp.generate_stories import GenerateStories
from rasa.nlu.training_data import TrainingData
from rasa.nlu.model import Interpreter, Trainer
from rasa.nlu.config import RasaNLUModelConfig

_LOGGER = logging.getLogger(__name__)

NLU_DEFAULT_LANGUAGE = "en"


class Nlp(Service):
    async def setup(self):
        _LOGGER.info("Starting NLU training.")
        if not os.path.exists('data/model'):
            data, domain_data, stories = GenerateStories.run("data",
                                                             self.config.get("language", NLU_DEFAULT_LANGUAGE))
        training_data = TrainingData(training_examples=data)

        pipeline = [
            {"name": "WhitespaceTokenizer"},
            {"name": "CRFEntityExtractor"},
            {"name": "EntitySynonymMapper"},
            {"name": "CountVectorsFeaturizer", "token_pattern": "(?u)\b\w+\b"},
            {"name": "EmbeddingIntentClassifier"}
        ]

        nlu_config = RasaNLUModelConfig({"language": self.config.get("language", NLU_DEFAULT_LANGUAGE),
                                         "pipeline": pipeline,
                                         "data": None})

        fixed_model_name = "model"
        trainer = Trainer(nlu_config, None, True)
        trainer.train(training_data)
        trainer.persist("data/model", None, fixed_model_name)

    @match_service('')
    async def parse(self, asm, services, message, config):
        text = GenerateStories.preprocessor(message.text, self.config.get("language", NLU_DEFAULT_LANGUAGE))

        if asm.config.get('interpreter') is None:
            asm.config.setdefault('interpreter',
                                  Interpreter.load("data/model/model",
                                                   None))

        interpreter = asm.config.get('interpreter')
        result = interpreter.parse(text)
