import os
import sys
import logging

from asm.manager.core import ArcusServiceManager
from asm.utils.logging import configure_logging


_LOGGER = logging.getLogger(__name__)


def main():
    configure_logging({})

    service_name = os.getenv('ARCUS_SERVICE', None)

    if service_name is None:
        _LOGGER.error("Error, service not defined!")
    else:
        with ArcusServiceManager(service_name, os.getenv('ARCUS_SERVICE_USER_DB', False)) as service:
            service.load()
            service.run()


if __name__ == '__main__':
    sys.exit(main())
