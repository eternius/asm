# -*- coding: utf-8 -*-
"""A module for asm to allow persist in mongo database."""
import logging
from functools import reduce

from motor.motor_asyncio import AsyncIOMotorClient

from asm.database import Database


class DatabaseMongo(Database):
    """A module for asm to allow memory to persist in a mongo database.
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
        logging.debug("Loaded mongo database connector")
        self.name = "mongo"
        self.config = config
        self.client = None
        self.database = None

    async def connect(self):
        """Connect to the database."""
        host = self.config["host"] if "host" in self.config else "localhost"
        port = str(self.config["port"]) if "port" in self.config else "27017"
        database = self.config["database"] if "database" in self.config else "arcus"
        path = "mongodb://" + host + ":" + port
        self.client = AsyncIOMotorClient(path)
        self.database = self.client[database]
        logging.info("Connected to mongo")

    async def put(self, collection, key, data):
        """Insert or replace an object into the database for a given key.
        Args:
            key (str): the key is the databasename
            data (object): the data to be inserted or replaced
        """
        logging.debug("Putting %s into mongo", key)
        if self.get(collection, key):
            await self.database[collection].update_one({"_id": key}, {"$set": data})
        else:
            data['_id'] = key
            await self.database[collection].insert_one(data)

    async def get(self, collection, key):
        """Get a document from the database (key).
        Args:
            key (str): the key is the databasename.
        """
        logging.debug("Getting %s from mongo", key)
        return await self.database[collection].find_one(
            {"$query": {"_id": key}, "$orderby": {"$natural": -1}}
        )

    async def get_keys(self, collection):
        """Return a list of keys.
        Args:
            collection (str): the collection is the databasename
        Returns:
            object or None: List of keys, or None if no
                            object found.
        """
        result = []
        cursor = self.database[collection].find()
        for document in await cursor.to_list(length=500):
            result.append(document['_id'])
        return result
