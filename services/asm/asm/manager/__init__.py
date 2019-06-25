import copy
import os
import signal
import sys
import weakref
import asyncio
import contextlib
import logging
import inspect

from asm.nlp import NLP
from asm.utils.web import Web
from asm.utils.loader import Loader
from asm.connector import Connector
from asm.service import Service
from asm.database import Database
from asm.database import Memory
from asm.utils import events

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

        self.nlps = []
        self.config = {}
        self.services = []
        self.services_tasks = []
        self.connectors = []
        self.connector_tasks = []
        self.loader = Loader(self)

        self.stats = {
            "messages_parsed": 0,
            "webhooks_called": 0,
            "total_response_time": 0,
            "total_responses": 0,
        }

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
        self.config = self.loader.load_config_from_file(self.name)
        self.modules = self.loader.load_modules_from_config(self.config)
        _LOGGER.debug("Loaded %i services", len(self.modules["services"]))
        self.get_functions(self.modules["services"])

        if 'nlp' in self.config:
            _LOGGER.debug("Loaded %i nlp engines", len(self.modules["nlp"]))
            self.get_nlp_engine(self.modules["nlp"])

        if len(self.config['databases']) > 0:
            self.start_databases(self.modules["databases"])

        self.setup_services(self.modules["services"])
        if 'nlp' in self.config:
            self.train_nlp_engine(self.modules["nlp"])

        self.web_server = Web(self)
        self.web_server.setup_webhooks(self.services)

        asyncio.set_event_loop(self.eventloop)
        if self.modules["connectors"] is not None:
            self.start_connectors(self.modules["connectors"])
        self.eventloop.create_task(self.web_server.start())

    async def unload(self, future=None):
        """Stop the event loop."""
        _LOGGER.info("Received stop signal, exiting.")

        _LOGGER.info("Removing services...")
        for service in self.services:
            _LOGGER.info("Removed %s", service)
            self.services.remove(service)

        if self.connectors is not None:
            for connector in self.connectors:
                _LOGGER.info("Stopping connector %s...", connector.name)
                await connector.disconnect()
                self.connectors.remove(connector)
                _LOGGER.info("Stopped connector %s", connector.name)

        if 'nlp' in self.config:
            _LOGGER.info("Removing nlp engine...")
            for nlp in self.nlps:
                _LOGGER.info("Removed %s", nlp)
                self.nlps.remove(nlp)

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

    def get_functions(self, services_list):
        """Iterates through all the services which have been loaded and get
        functions which have been defined in the service.
        Args:
            services_list (list): A list of all the loaded services.
        """
        for service in services_list:
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

    def get_nlp_engine(self, services_list):
        """Iterates through all the nlp engines which have been loaded and get
        functions which have been defined in the nlp engine.
        Args:
            services_list (list): A list of all the loaded nlp engines.
        """
        for service in services_list:
            for func in service["module"].__dict__.values():
                if isinstance(func, type) and issubclass(func, NLP) and func != NLP:
                    service_obj = func(self, service["config"])

                    for name in service_obj.__dir__():
                        try:
                            method = getattr(service_obj, name)
                        except Exception:
                            continue

                        if hasattr(method, "nlp"):
                            self.nlps.append(method)

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
                    service = cls(self, service_module["config"])
                    services_list.append(service)

        if services_list:
            for service in services_list:
                self.eventloop.run_until_complete(service.setup())
        else:
            self.critical("All services failed to setup", 1)

    def train_nlp_engine(self, modules):
        """Call train method for the nlp engine."""
        nlp_engines_list = []
        for nlp_engine_module in modules:
            for _, cls in nlp_engine_module["module"].__dict__.items():
                if (
                        isinstance(cls, type)
                        and issubclass(cls, NLP)
                        and cls is not NLP
                ):
                    nlp = cls(self, nlp_engine_module["config"])
                    nlp_engines_list.append(nlp)

        if nlp_engines_list:
            for nlp_engine in nlp_engines_list:
                self.eventloop.run_until_complete(nlp_engine.train())
        else:
            self.critical("All nlp engines failed to train", 1)

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

    async def parse(self, event):
        """Parse a string against all skills."""
        self.stats["messages_parsed"] = self.stats["messages_parsed"] + 1
        tasks = []
        if isinstance(event, events.Event):
            _LOGGER.debug("Parsing input: %s", event)

            tasks.append(self.eventloop.create_task(self.run_service(self.services[0],
                                                                     self.services[0].config,
                                                                     event)))
        return tasks

    async def run_service(self, service, config, message):
        """Execute a service."""
        # pylint: disable=broad-except
        # We want to catch all exceptions coming from a service module and not
        # halt the application. If a skill throws an exception it just doesn't
        # give a response to the user, so an error response should be given.
        try:
            if len(inspect.signature(service).parameters.keys()) > 1:
                await service(self, config, message)
            else:
                await service(message)
        except Exception:
            if message:
                await message.respond(
                    events.Message("Whoops there has been an error")
                )
                await message.respond(events.Message("Check the log for details"))

            _LOGGER.exception("Exception when running skill '%s' ", str(config["name"]))

    async def run_nlp(self, nlp, config, message):
        """Execute a service."""
        # pylint: disable=broad-except
        # We want to catch all exceptions coming from a service module and not
        # halt the application. If a skill throws an exception it just doesn't
        # give a response to the user, so an error response should be given.
        try:
            if len(inspect.signature(nlp).parameters.keys()) > 1:
                return await nlp(self, config, message)
            else:
                return await nlp(message)
        except Exception:
            _LOGGER.exception("Exception when running nlp engine '%s' ", str(config["name"]))
            return None

    async def send(self, event):
        """Send an event.
        If ``event.connector`` is not set this method will use
        `ArcusServiceManager.default_connector`. If ``event.connector`` is a string, it
        will be resolved to the name of the connectors configured in this
        instance.
        Args:
            event (asm.events.Event): The event to send.
        """
        if isinstance(event.connector, str):
            event.connector = self._connector_names[event.connector]

        if not event.connector:
            event.connector = self.default_connector

        return await event.connector.send(event)
