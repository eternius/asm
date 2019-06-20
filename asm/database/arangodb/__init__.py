# -*- coding: utf-8 -*-
"""A module for asm to allow persist in arangodb database."""
import logging
from pyArango.connection import *
from pyArango.theExceptions import DocumentNotFoundError

from asm.database import Database


class DatabaseArangoDB(Database):
    """A module for service to allow memory to persist in a mongo database.
    Attributes:
    """

    def __init__(self, config, asm=None):
        """Create the connection.
        Set some basic properties from the database config such as the name
        of this database.
        Args:
            config (dict): The config for this database specified in the
                           `configuration.yaml` file.
        """
        super().__init__(config, asm=asm)
        logging.debug("Loaded arangodb database connector")
        self.name = "arangodb"
        self.config = config
        self.client = None
        self.database = None

    async def connect(self):
        """Connect to the database."""
        host = self.config["host"] if "host" in self.config else "arangodb"
        port = self.config["port"] if "port" in self.config else "8529"
        user = self.config["user"] if "user" in self.config else "root"
        password = self.config["password"] if "password" in self.config else "arcusarcus"
        database = self.config["database"] if "database" in self.config else "arcus"
        self.client = Connection(arangoURL="http://" + host + ":" + port,
                                 username=user,
                                 password=password)
        if database in self.client.databases:
            self.database = self.client[database]
        else:
            self.database = self.client.createDatabase(name=database)
        logging.info("Connected to arangodb")

    async def put(self, collection, key, data):
        """Insert or replace an object into the database for a given key.
        Args:
            collection (str): the collection is the databasename
            key (str): the key is key value
            data (object): the data to be inserted or replaced
        """
        logging.debug("Putting %s into arangodb", key)

        save = False
        doc = await self.get(collection, key)
        if doc is None:
            coll = await self._get_collection(collection)
            doc = coll.createDocument()
            doc._key = key
            save = True

        for key, value in data.items():
            doc[key] = value

        if save:
            doc.save()
        else:
            doc.patch()

    async def get(self, collection, key):
        """Get a document from the database (key).
        Args:
            collection (str): the collection is the databasename
            key (str): the key is key value
        """
        logging.debug("Getting %s from arangodb", key)
        coll = await self._get_collection(collection)

        try:
            return coll[key]
        except DocumentNotFoundError:
            return None

    async def get_keys(self, collection):
        """Return a list of keys.
        Args:
            collection (str): the collection is the databasename
        Returns:
            object or None: List of keys, or None if no
                            object found.
        """
        return self.database.AQLQuery("FOR x IN " + collection + " RETURN x._key", rawResults=True, batchSize=100)

    async def _get_collection(self, name):
        if self.database.hasCollection(name):
            return self.database[name]
        return self.database.createCollection(name=name)
