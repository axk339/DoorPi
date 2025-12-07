"""Actions related to pin output: out"""
import threading
from typing import Any, Mapping

import doorpi
import logging
from threading import Thread

from . import Action

LOGGER = logging.getLogger(__name__)


class OutAction(Action):
    """Sets a GPIO pin to a constant value."""

    def __init__(self, pin: str, value: str) -> None:
        super().__init__()
        self._pin = pin
        self._value = value

    def __call__(self, event_id: str, extra: Mapping[str, Any]) -> None:
        del event_id, extra
        self._setpin(self._value)

    def _setpin(self, value: str) -> None:
        if not doorpi.INSTANCE.keyboard.output(self._pin, value):
            raise RuntimeError(f"Cannot set pin {self._pin} to {value}")

    def __str__(self) -> str:
        return f"Set {self._pin} to {self._value}"

    def __repr__(self) -> str:
        return f"out:{self._pin},{self._value}"


class TriggeredOutAction(OutAction):
    """Holds a GPIO pin at a value for some time before setting it back."""

    def __init__(
        self,
        pin: str,
        startval: str,
        stopval: str,
        holdtime: str,
        waittime: str = 0,
        loops: str = 1,
        intpin: str = None,
        /,
    ) -> None:
        super().__init__(pin, startval)
        self._stopval = stopval
        self._holdtime = float(holdtime)/1000
        self._waittime = float(waittime)/1000
        self._loops = int(loops)
        self._intpin = intpin
        self._int = threading.Event()
        self._running = False
        if intpin:
            doorpi.INSTANCE.event_handler.register_action(
                f"OnKeyDown_{intpin}", self.interrupt
            )

    def __call__(self, event_id: str, extra: Mapping[str, Any]) -> None:
        thrf = Thread (target=self._run_callthread, args=[])
        thrf.start()
        LOGGER.info ("OUT: thread started")
    
    def _run_callthread(self) -> None:
        count = self._loops
        self._running = True
        while count != 0:
            LOGGER.info ("OUT: setpin, loops=" + str(count))
            self._setpin(self._value)
            self._int.clear()  # Make sure the flag is not set before waiting for it
            if self._int.wait(timeout=self._holdtime):
                count = 0      # Stop directly if interrupt fired
            LOGGER.debug ("OUT: set stopval")
            self._setpin(self._stopval)
            if count != 0:
                self._int.clear()  # Make sure the flag is not set before waiting for it
                if self._int.wait(timeout=self._waittime):
                    count = 0      # Stop directly if interrupt fired
                if count > 0: count -= 1
        self._running = False
        LOGGER.info ("OUT: finished out loops")

    def interrupt(self, event_id: str, extra: Mapping[str, Any]) -> None:
        """Aborts the wait time, so that the pin will be reset immediately."""
        del event_id, extra
        if self._running:
            LOGGER.info ("OUT: interrupt")
        else:
            LOGGER.debug ("OUT: interrupt, but not running")
        self._int.set()

    def __str__(self) -> str:
        return (
            " ".join(
                [f"Hold {self._pin} at {self._value} for {self._holdtime}ms",
                 f"wait {self._waittime}ms" if (self._waittime > 0) else "",
                 f"loop infinitly" if (self._loops < 0) else f"loop {self._loops} times",
                 f"or until {self._intpin} is pressed" if self._intpin else ""])
        )

    def __repr__(self) -> str:
        return "".join(
            (
                "out:",
                ",".join(
                    (
                        self._pin,
                        self._value,
                        self._stopval,
                        str(self._holdtime),
                        str(self._waittime),
                        str(self._loops),
                    )
                ),
                self._intpin or "",
            )
        )


def instantiate(*args: str) -> Action:
    """Create an ``out:`` action"""
    if len(args) <= 2:
        return OutAction(*args)
    return TriggeredOutAction(*args)
