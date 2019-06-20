# -*- coding: utf-8 -*-
"""A module for asm to allow persist in arangodb database."""
import logging
from pyArango.connection import *

from asm.database import Database


class DatabaseMongo(Database):
    """A module for service to allow memory to persist in a mongo database.
    Attributes:
    """

    def __init__(self, config, service=None):
        """Create the connection.
        Set some basic properties from the database config such as the name
        of this database.
        Args:
            config (dict): The config for this database specified in the
                           `configuration.yaml` file.
        """
        super().__init__(config, service=service)
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
        coll = self.database.createCollection(name=collection)
        doc = coll.createDocument()
        doc._key = key
        for key, value in data.items():
            doc[key] = value

        doc.save()

    async def get(self, collection, key):
        """Get a document from the database (key).
        Args:
            collection (str): the collection is the databasename
            key (str): the key is key value
        """
        logging.debug("Getting %s from arangodb", key)
        coll = self.database.createCollection(name=collection)

        return coll.coll[key]