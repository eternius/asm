"""Base class for class-based nlp engines."""
from functools import wraps


def _nlp_decorator(func):
    @wraps(func)
    def decorated_nlp(*args, **kwargs):
        return func(*args, **kwargs)

    decorated_nlp.config = func.__self__.config

    return decorated_nlp


class NLP:
    """A service prototype to use when creating classy nlp engines."""
    def __init__(self, asm, config, *args, **kwargs):
        """Create the service.
        Set some basic properties from the module.
        Args:
            asm (ArcusServiceManager): The running asm instance pointer.
            config (dict): The config for this module specified in the
                           `configuration.yaml` file.
        """
        super().__init__()

        self.asm = asm
        self.config = config

        for name in self.__dir__():
            try:
                method = getattr(self, name)
            except Exception:
                continue

            if hasattr(method, "matchers"):
                setattr(self, name, _nlp_decorator(method))

    async def train(self):
        """Train the engine.
        """
        pass

    async def parse_text(self, text):
        """Train the engine.
        """
        pass

    async def get_response(self, request):
        """Train the engine.
        """
        pass

    async def generic_action(self, request):
        """Call generic action for the engine.
        """
        pass
