"""Actions related to executing other processes: os_execute"""
import logging
import subprocess
from typing import Any, Mapping

from . import Action
import doorpi

LOGGER = logging.getLogger(__name__)
RUNNING = False


class OSExecuteAction(Action):
    """Executes a command
       optionally this subproc is restricticted to <restrict> parallel processes"""

    def __init__(self, cmd: str, restricted: bool = False) -> None:
        super().__init__()
        self.__cmd = cmd.replace('!BASEPATH!', str(doorpi.INSTANCE.base_path))
        self.__restricted = restricted
        self.__running = False

    def __call__(self, event_id: str, extra: Mapping[str, Any]) -> None:
        if self.__restricted and self.__running:
            LOGGER.debug("This action is restricted to run only once")
            return

        LOGGER.debug("[%s] Executing shell command: %s", event_id, self.__cmd)
        self.__running = True
        result = subprocess.run(self.__cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if result.returncode == 0:
            LOGGER.debug("[%s] Command returned successfully", event_id)
        else:
            LOGGER.info(
                "[%s] Command returned with code %d",
                event_id,
                result.returncode,
            )
        self.__running = False

    def __str__(self) -> str:
        return f"Run shell code {self.__cmd}"

    def __repr__(self) -> str:
        return f"os_execute:{self.__cmd}"
