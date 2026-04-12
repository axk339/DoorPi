import logging
import doorpi
from doorpi.actions import Action

LOGGER = logging.getLogger(__name__)

class EventAction(Action):
    def __init__(self, event_name: str) -> None:
        super().__init__()
        self._event_name = event_name

    def __call__(self, event_id: str, extra: dict) -> None:
        eh = doorpi.INSTANCE.event_handler
        
        # Sicherstellen, dass die Quelle registriert ist
        # register_source ignoriert den Aufruf, wenn die Quelle schon bekannt ist
        try:
            eh.register_source("event_action")
            eh.register_event(self._event_name, "event_action")
        except:
            pass # Falls es in deiner Version anders implementiert ist

        LOGGER.info("Firing event '%s' via event_action", self._event_name)
        eh.fire_event(self._event_name, "event_action")

    def __str__(self) -> str:
        return f"Fire event {self._event_name}"

    def __repr__(self) -> str:
        return f"event:{self._event_name}"

