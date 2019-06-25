from rasa.core.interpreter import NaturalLanguageInterpreter


class LocalNLUInterpreter(NaturalLanguageInterpreter):
    def __init__(self, result):
        self.result = result

    async def parse(self, text, message_id=None):
        """Fake interpreter for rasa."""
        return self.result
