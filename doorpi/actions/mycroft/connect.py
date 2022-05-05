import logging

import doorpi

from HiveMind_presence.discovery import LocalDiscovery
from hivemind_bus_client.message import HiveMessage, HiveMessageType
from mycroft_bus_client import Message

LOGGER = logging.getLogger(__name__)

class MycroftConnect(object):
    """Singleton Class to spin up websocket connection to Mycroft instance"""
    _instance = None

    def __init__(self):
        raise RuntimeError('Call instance() instead')

    @classmethod
    def instance(cls):
        if cls._instance is None:
            LOGGER.debug("Creating new mycroft connect instance")
            cls._instance = cls.__new__(cls)
            cls.bus = None
            cls.connected = False

            conf = doorpi.INSTANCE.config.view("mycroft")
            cls.name = conf["hivename"]
            cls.__access_key = conf["access_key"]
            cls.__crypto_key = conf["crypto_key"]
            cls.host = conf["host"]

        return cls._instance

    def connecting(self, node):
        self.bus = node.connect(self.__access_key, crypto_key=self.__crypto_key)

    @property
    def connections(self):
        return self._connections

    def send_message(self, htype, mtype, text):
        _valid_htypes = [m.value for m in HiveMessageType]

        if not htype:
            htype = "bus"
        elif htype.lower() not in _valid_htypes:
            LOGGER.error(f"The first message type has to be one of {_valid_htypes}")
        if not mtype:
            mtype = "speak"
        else:
            mtype = mtype.lower()

        payload = Message(mtype,
                          data={'utterance': text},
                          context=self.create_context(htype, mtype, text))
        message = HiveMessage(htype, payload)

        received = None
        if self.bus is not None and self.connected:
            received = self.bus.wait_for_response(message)

        return received

    def create_context(self, htype, mtype, text):
        _ctxt = {}
        if mtype == "speak":
            _ctxt["destination"] = "audio"
        else:
            _ctxt["destination"] = "skills"

        return _ctxt

    def discover_hivemind(self):

        discovery = LocalDiscovery()
        discovery.on_new_node = self.connecting
        while not self.connected:
            self._connections = list(discovery.nodes.keys())
            self.connected = self.host in self._connections
            for node in discovery.scan():
                LOGGER.info("Fetching Node data: {name}, {url}".format(name=node.friendly_name, url=node.address))

        return self.connected