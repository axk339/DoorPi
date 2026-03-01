"""BRI 22.06.2025 Action that writes DoorPi snapshot status"""
import logging
import pathlib
import threading
from typing import Any, Mapping

import doorpi.actions
from doorpi.status.status_class import DoorPiStatus
from doorpi.actions import snapshot

import datetime

from . import Action

LOGGER = logging.getLogger(__name__)

# Globales Lock für dieses Modul
_EVENTS_LOCK = threading.Lock()

#/home/pi/DoorPi/DoorPi.egg-info/entry_points.txt

class StatussnapAction(Action):
    """Writes custom-formatted DoorPi status to a file."""

    def __init__(self, filename: str, content: str) -> None:
        super().__init__()
        
        self.__content = content
        self.__logpath = filename
        self.nextFile()
    
    def nextFile(self):
        self.__filename = pathlib.Path(doorpi.INSTANCE.parse_string(self.__logpath) + "/doorpi_events.txt")
        
        self.__filename.parent.mkdir(parents=True, exist_ok=True)

    def __call__(self, event_id: str, extra: Mapping[str, Any]) -> None:
        
        # Alles innerhalb des Locks ausführen
        with _EVENTS_LOCK:
            try:
                self.nextFile()
                with self.__filename.open("a") as f:
                    f.write(self.__content+",1\n")
                    f.flush()
            except Exception:  # pylint: disable=broad-except
                LOGGER.exception(
                    "[%s] Error fetching status information for file %s",
                    event_id,
                    self.__filename,
                )
        

    def __str__(self) -> str:
        return f"Write current status into {self.__filename}"

    def __repr__(self) -> str:
        return f"statusfile:{self.__filename},{self.__content.strip()}"
