"""Actions that control event execution: sleep, waitevent"""
import threading
#from time import sleep
import time
from typing import Any, Mapping
import os
from pwd import getpwnam
import logging

import doorpi.actions
import doorpi.event

from . import Action

LOGGER = logging.getLogger(__name__)


class SleepAction(Action):
    """Delays event execution."""

    def __init__(self, time: str) -> None:
        super().__init__()
        self.__time = float(time)

    def __call__(self, event_id: str, extra: Mapping[str, Any]) -> None:
        time.sleep(self.__time)

    def __str__(self) -> str:
        return f"Wait for {self.__time} seconds"

    def __repr__(self) -> str:
        return f"sleep:{self.__time}"


class WaitEventAction(Action):
    """Waits for a different event to occur to perform an action."""

    def __init__(self, eventname: str, waittime: str, action: str) -> None:
        if action not in {"abort", "continue"}:
            raise ValueError("`action` must be `abort` or `continue`")

        self.__eventname = eventname
        self.__waittime = float(waittime)
        self.__action = action

        self.__flag = threading.Event()
        self.__cb = doorpi.actions.CallbackAction(self.__flag.set)
        doorpi.INSTANCE.event_handler.actions[eventname].insert(0, self.__cb)

    def __call__(self, event_id: str, extra: Mapping[str, Any]) -> None:
        self.__flag.clear()

        try:
            self.__flag.wait(self.__waittime)
        except TimeoutError:
            event_occured = False
        else:
            event_occured = True

        if (self.__action == "continue") ^ event_occured:
            raise doorpi.event.AbortEventExecution()

    def __str__(self) -> str:
        otheraction = "continue" if self.__action == "abort" else "abort"
        return "Wait for {}, then {} (otherwise {})".format(
            self.__eventname, self.__action, otheraction
        )

    def __repr__(self) -> str:
        return f"waitevent:{self.__eventname},{self.__action}"


class SkipAction(Action):
    """Skip further event execution if last event less x seconds."""

    def __init__(self, time: str) -> None:
        super().__init__()
        self.__time = float(time)

    def __call__(self, event_id: str, extra: Mapping[str, Any]) -> None:
        LOGGER.debug ("[" + event_id + "] prev_fired_dt=" + str(extra["prev_fired_dt"]) + ", last_fired_dt=" + str(extra["last_fired_dt"]))
        if extra["prev_fired_dt"] != None:
            if ((extra["last_fired_dt"] - extra["prev_fired_dt"]) < self.__time):
                raise doorpi.event.AbortEventExecution()

    def __str__(self) -> str:
        return f"Skip if repeat before {self.__time} seconds"

    def __repr__(self) -> str:
        return f"skip:{self.__time}"


class ConditionAction(Action):
    """Skip next action of event execution if last condition in text file true."""

    def __init__(self, matchtext: str, skip: str, path: str, filename: str) -> None:
        super().__init__()
        if matchtext.startswith("!"):
            self.__matchtext = matchtext[1:]
            self.__matchequal = False
        else:
            self.__matchtext = matchtext
            self.__matchequal = True
        if skip.startswith("#"):
            self.__skip = int(skip[1:])
            self.__chkchange = True
        else:
            self.__skip = int(skip)
            self.__chkchange = False
        self.__contentlast = ""
        self.__filename = filename
        self.__filepath = path + "/" + filename
        os.makedirs (path, exist_ok=True)
        if path.endswith("web"):
            uid = getpwnam("www-data").pw_uid
            gid = getpwnam("www-data").pw_gid
            os.chown(path, uid, gid)
        
    def __call__(self, event_id: str, extra: Mapping[str, Any]) -> None:
        try:
            with open(self.__filepath) as f:
                content = f.readline()
        except:
            content = ""
        # check conditon
        if self.__matchequal:
            # execute next commands if text found, skip otherwise
            chk = (content == self.__matchtext)
            text = "found"
        else:
            # execute next commands if text not found, skip otherwise
            chk = (content != self.__matchtext)
            text = "not found"
        # use conditon
        if chk:
            # check change
            if self.__chkchange:
                # execute next if change
                if self.__contentlast != content:
                    self.__contentlast = content
                    LOGGER.debug ("[" + event_id + "] '" + self.__matchtext + "' "+text+" first time in " + self.__filename + ", not skipping next " + str(self.__skip) + " actions")
                # skip next if change
                else:
                    LOGGER.debug ("[" + event_id + "] '" + self.__matchtext + "' "+text+" several times in " + self.__filename + ", skipping next " + str(self.__skip) + " actions")
                    raise doorpi.event.SkipEventExecution(self.__skip)
            # always execute if not checking change
            else:
                self.__contentlast = content
                LOGGER.debug ("[" + event_id + "] '" + self.__matchtext + "' "+text+" in " + self.__filename + ", not skipping next " + str(self.__skip) + " actions")
        # always skip if not found
        else:
            self.__contentlast = content
            LOGGER.debug ("[" + event_id + "] '" + self.__matchtext + "' not "+text+" in " + self.__filename + ", skipping next " + str(self.__skip) + " actions")
            raise doorpi.event.SkipEventExecution(self.__skip)
    
    def __str__(self) -> str:
        return f"Skip next {self.__skip} action if '{self.__matchtext}' in '{self.__filepath}'"

    def __repr__(self) -> str:
        return f"cond:{self.__matchtext}"

