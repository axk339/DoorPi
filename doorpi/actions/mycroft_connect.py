"""Actions related to executing other processes: os_execute"""
import logging
from typing import Any, Mapping

from . import Action
from .mycroft.connect import MycroftConnect

LOGGER = logging.getLogger(__name__)

INSTANCE = None


class MycroftConnectAction(Action):
    """Spins up websocket connection to Mycroft instance"""

    def __init__(self, *cmd: str) -> None:
        super().__init__()

    def __call__(self, event_id: str, extra: Mapping[str, Any]) -> None:

        mycroft = MycroftConnect.instance()
        connected = mycroft.discover_hivemind()

        connections = mycroft.connections

        if connected:
            LOGGER.info("DoorPi is connected with %s", connections)
        else:
            LOGGER.info("Couldn't connect in time")

    def __str__(self) -> str:
        return f"Connecting mycroft"

    def __repr__(self) -> str:
        return f"connect_mycroft:"