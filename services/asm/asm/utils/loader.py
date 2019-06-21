import os
import logging
import importlib.util
import yaml

from pkg_resources import iter_entry_points
from collections.abc import Mapping


_LOGGER = logging.getLogger(__name__)


class Loader:
    """Class to load in config and modules."""

    def __init__(self, asm):
        """Create object with opsdroid instance."""
        self.asm = asm
        self.modules_directory = None
        self.current_import_config = None
        _LOGGER.debug('Loaded loader')

    @staticmethod
    def is_builtin_module(config):
        """Check if a module is a builtin.
         Args:
            config: dict of config information related to the module
        Returns:
            bool: False if the module is not builtin
        """
        try:
            return importlib.util.find_spec(
                "asm.{module_type}.{module_name}".format(
                    module_type=config["type"], module_name=config["name"].lower()
                )
            )
        except ImportError:
            return False

    def _load_modules(self, modules_type, modules):
        """Install and load modules.
        Args:
            self: instance method
            modules_type: str with the type of module being loaded
            modules: list with module attributes
        Returns:
            list: modules and their config information
        """
        _LOGGER.debug("Loading %s modules...", modules_type)
        loaded_modules = []

        # entry point group naming scheme: service_ + module type plural,
        # eg. "service_databases"
        epname = "module_{}s".format(modules_type)
        entry_points = {ep.name: ep for ep in iter_entry_points(group=epname)}
        for epname in entry_points:
            _LOGGER.debug("Found installed package for %s '%s' support", modules_type, epname)

        for module in modules:

            # Set up module config
            config = module
            config = {} if config is None else config

            # We might load from a configuration file an item that is just
            # a string, rather than a mapping object
            if not isinstance(config, Mapping):
                config = {}
                config["name"] = module
                config["module"] = ""
            else:
                config["name"] = module["name"]
                config["module"] = module.get("module", "")
            config["type"] = modules_type
            config["is_builtin"] = self.is_builtin_module(config)
            if config["name"] in entry_points:
                config["entrypoint"] = entry_points[config["name"]]
            else:
                config["entrypoint"] = None
            config["module_path"] = self.build_module_import_path(config)
            config["install_path"] = self.build_module_install_path(config)

            # Import module
            self.current_import_config = config
            module = self.import_module(config)

            if module is not None:
                loaded_modules.append(
                    {"module": module, "config": config}
                )
            else:
                _LOGGER.error("Module %s failed to import.", config["name"])

        return loaded_modules

    @staticmethod
    def load_config_from_file(name):
        cfg_file = '/opt/arcus/conf/config.yml'
        if not os.path.exists(cfg_file):
            cfg_file = '/opt/arcus/conf/' + name + '.yml'

        with open(cfg_file, 'r') as stream:
            try:
                return yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                _LOGGER.error("Error loading config.yaml.", exc)
                return {"services": [], "databases": [], "connectors": []}

    def load_modules_from_config(self, config):
        """Load all module types based on config.
        Args:
            self: instance method
            config: dict of fields from configuration.yaml
        Returns:
            dict: containing connector, database, and skills
                fields from configuration.yaml
        """

        _LOGGER.debug("Loading modules from config...")

        connectors, databases, modules = None, None, None

        if "databases" in config.keys() and config["databases"]:
            databases = self._load_modules("database", config["databases"])

        if "services" in config.keys() and config["services"]:
            services = self._load_modules("service", config["services"])
        else:
            self.asm.critical("No services in configuration, at least 1 required"), 1

        connectors = self._load_modules("connector", config["connectors"])

        return {"connectors": connectors, "databases": databases, "services": services}

    @staticmethod
    def build_module_import_path(config):
        """Generate the module import path from name and type.
        Args:
            config: dict of config information related to the module
        Returns:
            string: module import path
        """
        return "asm." + config["type"] + "." + config["name"].lower()

    @staticmethod
    def build_module_install_path(config):
        """Generate the module install path from name and type.
        Args:
            self: instance method
            config: dict of config information related to the module
        Returns:
            string: module install directory
        """
        return os.path.join('asm', config["type"], config["name"])

    @staticmethod
    def import_module(config):
        """Import module namespace as variable and return it.
        Args:
            config: dict of config information related to the module
        Returns:
            Module: Module imported from config
        """

        if config.get("entrypoint"):
            _LOGGER.debug("Loading entry point-defined module for %s", config["name"])
            return config["entrypoint"].load()

        module_spec = None
        namespaces = [
            config["module_path"],
        ]
        for namespace in namespaces:
            try:
                module_spec = importlib.util.find_spec(namespace)
                if module_spec:
                    break
            except (ImportError, AttributeError):
                continue

        if module_spec:
            module = Loader.import_module_from_spec(module_spec)
            _LOGGER.info("Loaded %s: %s", config["type"], config["module_path"])
            return module

        _LOGGER.error('Failed to load %s: %s', config["type"], config["module_path"])
        return None

    @staticmethod
    def import_module_from_spec(module_spec):
        """Import from a given module spec and return imported module.
        Args:
            module_spec: ModuleSpec object containing name, loader, origin,
                submodule_search_locations, cached, and parent
        Returns:
            Module: Module imported from spec
        """
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        return module
