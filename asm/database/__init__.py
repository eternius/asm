import logging

_LOGGER = logging.getLogger(__name__)


class Database:
    """A base database.
    Database classes are used to persist key/value pairs in a database.
    """

    def __init__(self, config, asm=None):
        """Create the database.
        Set some basic properties from the database config such as the name
        of this database. It could also be a good place to setup properties
        to hold things like the database connection object and the database
        name.
        Args:
            config (dict): The config for this database specified in the
                           `configuration.yaml` file.
        """
        self.name = ""
        self.config = config
        self.asm = asm
        self.client = None
        self.database = None

    async def connect(self):
        """Connect to database service and store the connection object.
        This method should connect to the given database using a native
        python library for that database. The library will most likely involve
        a connection object which will be used by the put and get methods.
        This object should be stored in self.
        """
        raise NotImplementedError

    async def disconnect(self):
        """Disconnect from the database.
        This method should disconnect from the given database using a native
        python library for that database.
        """

    async def put(self, collection, key, data):
        """Store the data object in a database against the key.
        The data object will need to be serialised in a sensible way which
        suits the database being used and allows for reconstruction of the
        object.
        Args:
            collection (str): the collection is the databasename
            key (str): the key is key value
            data (object): The data object to store.
        Returns:
            bool: True for data successfully stored, False otherwise.
        """
        raise NotImplementedError

    async def get(self, collection, key):
        """Return a data object for a given key.
        Args:
            collection (str): the collection is the databasename
            key (str): the key is key value
        Returns:
            object or None: The data object stored for that key, or None if no
                            object found for that key.
        """
        raise NotImplementedError

    async def get_keys(self, collection):
        """Return a list of keys.
        Args:
            collection (str): the collection is the databasename
        Returns:
            object or None: List of keys, or None if no
                            object found.
        """
        raise NotImplementedError


class Memory:
    """A Memory object.
    An object to obtain, store and persist data outside of asm.
    Attributes:
        databases (:obj:`list` of :obj:`Database`): List of database objects.
        memory (:obj:`dict`): In-memory dictionary to store data.
    """

    def __init__(self):
        """Create object with minimum properties."""
        self.databases = []

    async def get_keys(self, collection):
        """Return a list of keys.
        Args:
            collection (str): the collection is the databasename
        Returns:
            object or None: List of keys, or None if no
                            object found.
        """
        _LOGGER.debug("Getting %s from memory.", collection)
        results = []
        for database in self.databases:
            results.append(await database.get_keys(collection))
        return results[0]

    async def get(self, collection, key):
        """Get data object for a given key.
        Gets the key value found in-memory or from the database(s).
        Args:
            collection (str): database.
            key (str): Key to retrieve data.
        Returns:
            A data object for the given key, otherwise `None`.
        """
        _LOGGER.debug("Getting %s from memory.", collection, key)
        results = []
        for database in self.databases:
            results.append(await database.get(collection, key))
        return results[0]

    async def put(self, collection, key, data):
        """Put a data object to a given key.
        Stores the key and value in memory and the database(s).
        Args:
            collection (str): database.
            key (str): Key for the data to store.
            data (obj): Data object to store.
        """
        _LOGGER.debug("Putting %s to memory", collection, key)
        if self.databases:
            for database in self.databases:
                await database.put(collection, key, data)
