import logging
from typing import Any, Mapping

from . import Action
from .mycroft.connect import MycroftConnect

LOGGER = logging.getLogger(__name__)


class MycroftSendAction(Action):
    """Sends a message/action over to Mycroft"""

    def __init__(self, payload: str = '', msgtype: str = '', hivetype: str = '') -> None:
        super().__init__()
        self.hivetype = hivetype
        self.msgtype = msgtype
        self.text = payload

    def __call__(self, event_id: str, extra: Mapping[str, Any]) -> None:

        mycroft = MycroftConnect.instance()
        if not mycroft.connected:
            return

        sent = mycroft.send_message(self.text, self.msgtype, self.hivetype)
        if sent:
            LOGGER.debug("Message sent to Mycroft")
        else:
            LOGGER.error("Couldn't send the message")

    def __str__(self) -> str:
        return f"sending mycroft: {self.text},{self.msgtype},{self.hivetype}"

    def __repr__(self) -> str:
        return f"to_mycroft: {self.text},{self.msgtype},{self.hivetype}"
