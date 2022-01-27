from typing import Any, Dict, Iterable, List

import doorpi.actions.snapshot
import doorpi.doorpi


def get(
    doorpi_obj: doorpi.doorpi.DoorPi,
    name: Iterable[str],
    value: Iterable[str],
) -> List[str]:
    del doorpi_obj, name, value

    path = str(doorpi.actions.snapshot.SnapshotAction.get_full_path())
    files: Iterable[str] = map(
        str, doorpi.actions.snapshot.SnapshotAction.list_all()
    )
    # because path is added by webserver automatically
    # TODO think this is a fragment and not needed any more
    if "DoorPiWeb" in path:
        changedpath = path[path.find("DoorPiWeb") + len("DoorPiWeb"):]
        files = [f.replace(path, changedpath) for f in files]
    return files

def is_active(doorpi_obj: doorpi.doorpi.DoorPi) -> bool:
    del doorpi_obj
    return True
