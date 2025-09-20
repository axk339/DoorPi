"""BRI 20.09.2025 Action that gets and writes akuvox status"""
import logging
import pathlib
from typing import Any, Mapping

import doorpi.actions
from doorpi.status.status_class import DoorPiStatus
from doorpi.actions import snapshot

import datetime

from . import Action

LOGGER = logging.getLogger(__name__)

#/home/pi/DoorPi/DoorPi.egg-info/entry_points.txt

class AkuvoxAction(Action):
    """Gets Akuvox status or sends update."""

    def __init__(self, filename: str, *content: str) -> None:
        super().__init__()
        
        self.__content = ",".join(content).strip()
        self.__logpath = filename
        self.nextFile()
    
    def nextFile(self):
        self.__filename = pathlib.Path(doorpi.INSTANCE.parse_string(self.__logpath) + "/doorpi_events.txt")
        
        self.__filename.parent.mkdir(parents=True, exist_ok=True)

    def __call__(self, event_id: str, extra: Mapping[str, Any]) -> None:
        content = doorpi.INSTANCE.parse_string(self.__content)
        
        try:
            self.nextFile()
            with self.__filename.open("a") as f:
                f.write(content+",1\n")
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
