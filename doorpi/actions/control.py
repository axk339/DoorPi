"""Actions that control event execution: sleep, waitevent"""
import threading
#from time import sleep
import time
from typing import Any, Mapping
import os
from pwd import getpwnam

import doorpi.actions
import doorpi.event

from . import Action


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
        if extra["last_finished"] != None:
            if ((time.time() - extra["last_finished"]) < self.__time):
                raise doorpi.event.AbortEventExecution()

    def __str__(self) -> str:
        return f"Skip if repeat before {self.__time} seconds"

    def __repr__(self) -> str:
        return f"skip:{self.__time}"


class ConditionAction(Action):
    """Skip next action of event execution if last condition in text file true."""

    def __init__(self, matchtext: str, skip: str, path: str, filename: str) -> None:
        super().__init__()
        self.__matchtext = matchtext
        self.__skip = int(skip)
        self.__filepath = path + "/" + filename
        os.makedirs (path, exist_ok=True)
        #not needed anymore
        #uid = getpwnam("www-data").pw_uid
        #gid = getpwnam("www-data").pw_gid
        #os.chown(path, uid, gid)
        
    def __call__(self, event_id: str, extra: Mapping[str, Any]) -> None:
        with open(self.__filepath) as f:
            content = f.readline()
        if (content == self.__matchtext):
            raise doorpi.event.SkipEventExecution(self.__skip)

    def __str__(self) -> str:
        return f"Skip next {self.__skip} action if '{self.__matchtext}' in '{self.__filepath}'"

    def __repr__(self) -> str:
        return f"cond:{self.__matchtext}"

