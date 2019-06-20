"""Base class for class-based services."""
from functools import wraps


def _service_decorator(func):
    @wraps(func)
    def decorated_service(*args, **kwargs):
        return func(*args, **kwargs)

    decorated_service.config = func.__self__.config

    return decorated_service


class Service:
    """A service prototype to use when creating classy services."""
    def __init__(self, config, asm, *args, **kwargs):
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
                setattr(self, name, _service_decorator(method))

    async def setup(self):
        """Setup the service.
        """
        pass
