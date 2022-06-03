import logging
from typing import Any, Mapping

from . import Action
from .mycroft.connect import MycroftConnect

LOGGER = logging.getLogger(__name__)


class MycroftSendAction(Action):
    """Sends a message/action over to Mycroft"""

    def __init__(self, hivetype: str = '', msgtype: str = '', payload:str = '') -> None:
        super().__init__()
        self.hivetype = hivetype
        self.msgtype = msgtype
        self.text = payload

    def __call__(self, event_id: str, extra: Mapping[str, Any]) -> None:

        mycroft = MycroftConnect.instance()
        if not mycroft.connected:
            return

        sent = mycroft.send_message(self.hivetype, self.msgtype, self.text)
        if sent:
            LOGGER.info("Message sent to Mycroft")
        else:
            LOGGER.info("Couldn't send the message")

    def __str__(self) -> str:
        return f"sending mycroft: {self.hivetype}, {self.msgtype}, {self.text}"

    def __repr__(self) -> str:
        return f"mycroft_send: {self.hivetype}, {self.msgtype}, {self.text}"