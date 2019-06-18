import os
import sys
import logging

from asm.manager.core import ArcusServiceManager
from asm.utils.logging import configure_logging


_LOGGER = logging.getLogger(__name__)


def main():
    configure_logging({})

    with ArcusServiceManager() as service:
        service.load()
        service.run()


if __name__ == '__main__':
    sys.exit(main())
