import operator
from typing import Any, Dict, Iterable

import doorpi.doorpi

import logging
LOGGER = logging.getLogger(__name__)

def get(
    doorpi_obj: doorpi.doorpi.DoorPi,
    name: Iterable[str],
    value: Iterable[str],
) -> Dict[str, Any]:
    del value
    name = ["name", "current_call"]
    status_getters = {
        "name": operator.methodcaller("get_name"),
        "current_call": operator.methodcaller("dump_call"),
    }
    return {
        n: status_getters[n](doorpi_obj.sipphone)
        for n in name
        if n in status_getters
    }


def is_active(doorpi_object: doorpi.doorpi.DoorPi) -> bool:
    return bool(doorpi_object.sipphone)
