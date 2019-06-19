import os
import sys
import logging

from asm.manager.core import ArcusServiceManager
from asm.utils.logging import configure_logging
from asm.operator.operator import Operator


_LOGGER = logging.getLogger(__name__)


def main():
    service_name = os.getenv('ARCUS_SERVICE', "dummy")

    configure_logging({})

    with ArcusServiceManager() as service:
        if service_name == "operator":
            service.eventloop.run_until_complete(Operator().check_core_platform())
        service.load()
        service.run()


if __name__ == '__main__':
    sys.exit(main())
