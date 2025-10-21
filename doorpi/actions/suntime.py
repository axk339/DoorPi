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

from .suntimeLib import suntime
import datetime
import logging

LOGGER = logging.getLogger(__name__)

class SuntimeTimer:
    def __init__(self, lat, lng) -> None:
        self.suntime = suntime(lat, lng)
        self.lastUpdate = datetime.datetime (1900, 1, 1)

    def update(self, now) -> None:
        #now = datetime.datetime.now()
        if now.day != self.lastUpdate.day:
            self.AMh, self.AMm, self.UMh, self.UMm = self.suntime.Suntime (1)
            LOGGER.info ("Updating suntime - Aufgang " + str(self.AMh) + ":" + str(self.AMm) + ", Untergang " + str(self.UMh) + ":" + str(self.UMm))
            self.lastUpdate = now

    def isDay(self) -> bool:
        now = datetime.datetime.now()
        self.update (now)  # check if update needed (once a day)
        if (now.hour > self.AMh) and (now.hour < self.UMh):
            return True
        else:
            if (now.hour == self.AMh) and (now.minute > self.AMm):
                return True
            if (now.hour == self.UMh) and (now.minute < self.UMm):
                return True
            return False

    def isNight(self) -> bool:
        return not self.isDay()

class SuntimeAction(Action):
    """Skip next action of event execution if day or night."""
    suntimeClass = None
    
    def __init__(self, event: str, skip: str) -> None:
        super().__init__()
        #ensure one single instance of suntimeClass
        if (SuntimeAction.suntimeClass==None):
            LOGGER.info ("Creating suntime instance lat="+str(doorpi.INSTANCE.config["suntime.latitude"])+", lng="+str(doorpi.INSTANCE.config["suntime.longitude"]))
            SuntimeAction.suntimeClass = SuntimeTimer(doorpi.INSTANCE.config["suntime.latitude"], doorpi.INSTANCE.config["suntime.longitude"])
        self.__event  = event
        if skip.startswith("#"):
            self.__skip = int(skip[1:])
            self.__chkchange = True
        else:
            self.__skip = int(skip)
            self.__chkchange = False
        self.__chkday = (event == "day")
        self.__event = event
        self.__last   = False

    def __call__(self, event_id: str, extra: Mapping[str, Any]) -> None:
        # check condition
        if self.__chkday:
            chk = self.suntimeClass.isDay()
        else:
            chk = self.suntimeClass.isNight()
        # use condition
        if chk:
            # checking change
            if self.__chkchange:
                # execute next command once
                if not self.__last:
                    LOGGER.debug (f"Found {self.__event} event 1st time, executing next command")
                    self.__last = chk
                # otherwise skip as well
                else:
                    LOGGER.debug (f"Found {self.__event} event several times, skipping next command")
                    raise doorpi.event.SkipEventExecution(self.__skip)
            # not checking change, next command always executed
            else:
                LOGGER.debug (f"Found {self.__event} event, executing next command")
                self.__last = chk
        # skip always if condition not met
        else:
            LOGGER.debug (f"Not found {self.__event} event, skipping next command")
            self.__last = chk
            raise doorpi.event.SkipEventExecution(self.__skip)

    def __str__(self) -> str:
        return f"Skip next {self.__skip} action if {self.__event}"

    def __repr__(self) -> str:
        return f"cond:{self.__event}"

