import os
import sys
import logging

from asm.manager import ArcusServiceManager
from asm.utils.logging import configure_logging
from asm.operator import Operator


_LOGGER = logging.getLogger(__name__)


def main():
    service_name = os.getenv('ARCUS_SERVICE', "dummy")

    configure_logging({})

    with ArcusServiceManager() as service:
        if service_name == "operator":
            arango_root_password = os.getenv('ARANGO_ROOT_PASSWORD', "arcusarcus")
            operator = Operator(arango_root_password)
            service.eventloop.run_until_complete(operator.platform.deploy_core_platform())
            service.eventloop.run_until_complete(operator.agent.deploy_agent('abot', 'es', ['abot']))
        service.load()
        service.run()


if __name__ == '__main__':
    sys.exit(main())
