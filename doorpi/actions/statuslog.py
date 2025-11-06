"""BRI 03.11.2024 Action that writes DoorPi status to a custom logfile"""
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

class StatuslogAction(Action):
    """Writes custom-formatted DoorPi status to a file."""

    def __init__(self, logpath: str, *content: str) -> None:
        super().__init__()
        
        self.__content = ",".join(content).strip()
        self.__logpath = logpath
        if not logpath.startswith("/"):
            self.__logpath = pathlib.Path(doorpi.INSTANCE.base_path, logpath)
        self.nextFile()
    
    def nextFile(self):
        prefix = datetime.datetime.now().strftime("%Y-%m-%d")
        pathext = datetime.datetime.now().strftime("%Y-%m")
        self.__filename = pathlib.Path(doorpi.INSTANCE.parse_string(self.__logpath) + "/" + pathext + "/doorpi_" + prefix + ".log")
        
        self.__filename.parent.mkdir(parents=True, exist_ok=True)
        
        if not self.__filename.is_file():
            with self.__filename.open("a") as f:
                f.write("timestamp,action,snapshot\n")

    def __call__(self, event_id: str, extra: Mapping[str, Any]) -> None:
        content = doorpi.INSTANCE.parse_string(self.__content)
        
        try:
            self.nextFile()
            snap_len = len(str(doorpi.INSTANCE.config["snapshots.directory"])) + len(str(doorpi.INSTANCE.base_path)) + 2
            snapfile = str(snapshot.SnapshotAction.list_all()[-1])[snap_len:]
            prefix = datetime.datetime.now().strftime("%Y.%m.%d %H:%M:%S")
            rec = "none"
            if doorpi.sipphone.from_pjsua2.fileio.RECORDER_latest != None:
                rec = doorpi.sipphone.from_pjsua2.fileio.RECORDER_latest
            #LOGGER.info ("Rec=" + str(rec))
            with self.__filename.open("a") as f:
                f.write(prefix+","+content+","+snapfile+","+rec+"\n")
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

