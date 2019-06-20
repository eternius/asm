import logging

from asm.operator.platform import Platform
from asm.operator.agent import Agent

_LOGGER = logging.getLogger(__name__)


class Operator:
    def __init__(self, arango_root_password):
        self.platform = Platform(arango_root_password)
        self.agent = Agent(arango_root_password)
