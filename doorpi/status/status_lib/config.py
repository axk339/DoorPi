from typing import Any, Iterable, Tuple

import doorpi.doorpi

# TODO dunno where description is coming from
locked = ("keyboard.*", "keyboard.*.description")


def get(
    doorpi_obj: doorpi.doorpi.DoorPi,
    name: Iterable[str],
    value: Iterable[str],
) -> Any:
    return_dict = {}
    for keypath in name:
        if keypath in locked:
            continue
        section = keypath.split(".")[0] if "." in keypath else "basics"
        if section not in return_dict:
            return_dict[section] = {}
        _definition = _format_definition(doorpi_obj.config[keypath],
                                         doorpi_obj.config.get_definition(keypath))
        return_dict[section][keypath] = _definition
    return return_dict


def is_active(doorpi_object: doorpi.doorpi.DoorPi) -> bool:
    return bool(doorpi_object.config)


def _format_definition(value: Any, definition: dict) -> Tuple:
    _type = str(definition["_type"])
    if "_membertype" in definition:
        _type = f"{_type} of {definition['_membertype']}"
    _default = definition["_default"]

    return value, _default, _type, definition["_description"]