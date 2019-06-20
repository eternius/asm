import copy
import os
import signal
import sys
import weakref
import asyncio
import contextlib
import logging

from asm.utils.web import Web
from asm.utils.loader import Loader
from asm.connector import Connector
from asm.service import Service
from asm.database import Database
from asm.database import Memory

_LOGGER = logging.getLogger(__name__)


class ArcusServiceManager:
    instances = []

    def __init__(self):
        self.name = os.getenv('ARCUS_SERVICE', "dummy")
        self._running = False
        self.sys_status = 0
        self.modules = {}
        self.web_server = None
        self.cron_task = None
        self.stored_path = []
        self.memory = Memory()

        self.eventloop = asyncio.get_event_loop()
        if os.name != "nt":
            for sig in (signal.SIGINT, signal.SIGTERM):
                self.eventloop.add_signal_handler(
                    sig, lambda: asyncio.ensure_future(self.handle_signal())
                )

        self.config = {}
        self.services = []
        self.services_tasks = []
        self.connectors = []
        self.connector_tasks = []
        self.loader = Loader(self)

    def __enter__(self):
        """Add self to existing instances."""
        self.stored_path = copy.copy(sys.path)
        if not self.__class__.instances:
            self.__class__.instances.append(weakref.proxy(self))
        else:
            self.critical("service has already been started", 1)

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Remove self from existing instances."""
        sys.path = self.stored_path
        self.__class__.instances = []
        asyncio.set_event_loop(asyncio.new_event_loop())

    def critical(self, error, code):
        """Exit due to unrecoverable error."""
        self.sys_status = code
        _LOGGER.critical(error)
        self.exit()

    def is_running(self):
        """Check whether service is running."""
        return self._running

    async def handle_signal(self):
        """Handle signals."""
        self._running = False

        await self.unload()

    def load(self):
        self.config = self.loader.load_config_from_file()
        self.modules = self.loader.load_modules_from_config(self.config)
        _LOGGER.debug("Loaded %i services", len(self.modules["services"]))
        self.get_functions(self.modules["services"])
        self.setup_services(self.modules["services"])

        self.web_server = Web(self)
        self.web_server.setup_webhooks(self.services)

        if len(self.config['databases']) > 0:
            self.start_databases(self.modules["databases"])

        self.start_connectors(self.modules["connectors"])
        self.eventloop.create_task(self.web_server.start())

    async def unload(self, future=None):
        """Stop the event loop."""
        _LOGGER.info("Received stop signal, exiting.")

        _LOGGER.info("Removing services...")
        for service in self.services:
            _LOGGER.info("Removed %s", service.config["name"])
            self.services.remove(service)

        for connector in self.connectors:
            _LOGGER.info("Stopping connector %s...", connector.name)
            await connector.disconnect()
            self.connectors.remove(connector)
            _LOGGER.info("Stopped connector %s", connector.name)

        if len(self.config['databases']) > 0:
            for database in self.memory.databases:
                _LOGGER.info("Stopping database %s...", database.name)
                await database.disconnect()
                self.memory.databases.remove(database)
                _LOGGER.info("Stopped database %s", database.name)

        if self.web_server is not None:
            _LOGGER.info("Stopping web server...")
            await self.web_server.stop()
            self.web_server = None
            _LOGGER.info("Stopped web server")

        if self.cron_task is not None:
            _LOGGER.info("Stopping cron...")
            self.cron_task.cancel()
            self.cron_task = None
            _LOGGER.info("Stopped cron")

        _LOGGER.info("Stopping pending tasks...")
        tasks = asyncio.Task.all_tasks()
        for task in list(tasks):
            if not task.done() and task is not asyncio.Task.current_task():
                task.cancel()

        _LOGGER.info("Stopped pending tasks")

    def run(self):
        """Start the event loop."""
        _LOGGER.info(self.name + " is now running, press ctrl+c to exit.")
        if not self.is_running():
            self._running = True
            while self.is_running():
                pending = asyncio.Task.all_tasks()
                with contextlib.suppress(asyncio.CancelledError):
                    self.eventloop.run_until_complete(asyncio.gather(*pending))

            self.eventloop.stop()
            self.eventloop.close()

            _LOGGER.info("Bye!")
            self.exit()
        else:
            _LOGGER.error("Oops! " + self.name + " is already running.")

    def exit(self):
        """Exit application."""
        _LOGGER.info("Exiting application with return code %s", str(self.sys_status))

        sys.exit(self.sys_status)

    def start_connectors(self, connectors):
        """Start the connectors."""
        for connector_module in connectors:
            for _, cls in connector_module["module"].__dict__.items():
                if (
                        isinstance(cls, type)
                        and issubclass(cls, Connector)
                        and cls is not Connector
                ):
                    connector = cls(connector_module["config"], self)
                    self.connectors.append(connector)

        if connectors:
            for connector in self.connectors:
                if self.eventloop.is_running():
                    self.eventloop.create_task(connector.connect())
                else:
                    self.eventloop.run_until_complete(connector.connect())
            for connector in self.connectors:
                task = self.eventloop.create_task(connector.listen())
                self.connector_tasks.append(task)
        else:
            self.critical("All connectors failed to load", 1)

    def get_functions(self, services):
        """Iterates through all the services which have been loaded and get
        functions which have been defined in the service.
        Args:
            services (list): A list of all the loaded services.
        """
        for service in services:
            for func in service["module"].__dict__.values():
                if isinstance(func, type) and issubclass(func, Service) and func != Service:
                    service_obj = func(self, service["config"])

                    for name in service_obj.__dir__():
                        try:
                            method = getattr(service_obj, name)
                        except Exception:
                            continue

                        if hasattr(method, "service"):
                            self.services.append(method)

                    continue

    def setup_services(self, modules):
        """Call setup method for the services."""
        services_list = []
        for service_module in modules:
            for _, cls in service_module["module"].__dict__.items():
                if (
                        isinstance(cls, type)
                        and issubclass(cls, Service)
                        and cls is not Service
                ):
                    service = cls(service_module["config"], self)
                    services_list.append(service)

        if services_list:
            for service in services_list:
                self.eventloop.run_until_complete(service.setup())
        else:
            self.critical("All services failed to setup", 1)

    def start_databases(self, databases):
        """Start the databases."""
        for database_module in databases:
            for name, cls in database_module["module"].__dict__.items():
                if (
                    isinstance(cls, type)
                    and issubclass(cls, Database)
                    and cls is not Database
                ):
                    _LOGGER.debug("Adding database: %s", name)
                    database = cls(database_module["config"])
                    self.memory.databases.append(database)
                    self.eventloop.run_until_complete(database.connect())
