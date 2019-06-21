import os
import logging
import asyncio

from asm.connector import Connector, register_event
from asm.utils.events import Message
from gmqtt import Client as MQTTClient
from gmqtt.mqtt.constants import MQTTv311


_LOGGER = logging.getLogger(__name__)


class Mqtt(Connector):
    def __init__(self, config, asm=None):
        self.name = "mqtt"
        self.config = config
        self.asm = asm
        self.default_room = "MyDefaultRoom"
        self.client = None

    async def connect(self):
        self.client = MQTTClient(self.asm.name)
        self.client.on_message = on_message
        self.client.set_auth_credentials(os.getenv('MQTT_USER', "arcus"), os.getenv('MQTT_PASSWORD', "arcusarcus"))
        await self.client.connect(os.getenv('MQTT_HOST', "mqtt"), 1883, keepalive=60, version=MQTTv311)

        _LOGGER.info("Connected to MQTT")

    async def listen(self):
        self.client.subscribe(self.asm.name + "/#", qos=1)
        stop = asyncio.Event()
        await stop.wait()

    @register_event(Message)
    async def respond(self, message):
        self.client.publish(self.asm.name, 'Message payload', response_topic='RESPONSE/TOPIC')

    async def disconnect(self):
        # Disconnect from the service
        await self.client.disconnect()


def on_message(client, topic, payload, qos, properties):
    print('RECV MSG:', topic, payload.decode(), properties)
