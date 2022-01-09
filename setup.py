#!/usr/bin/env python3

"""DoorPi Setup"""

from pathlib import Path
from os.path import basename
import sys

import setuptools

BASE_PATH = Path(__file__).resolve().parent
PACKAGE = basename(BASE_PATH)
PROJECT = PACKAGE.lower()
PREFIX = sys.prefix

ETC = "/etc" if sys.prefix == "/usr" else "etc"

datapath = BASE_PATH / "data"
substkeys = {
    "package": PACKAGE,
    "project": PROJECT,
    "prefix": PREFIX,
    "cfgdir": Path(PREFIX if PREFIX == "/usr" else "", "etc", PACKAGE
    ),
}
for file in datapath.iterdir():
    if file.suffix != ".in":
        continue
    content = file.read_text()
    for key, val in substkeys.items():
        content = content.replace(f"!!{key}!!", str(val))
    file.with_suffix("").write_text(content)

setuptools.setup(
    data_files=[
        # init script and systemd service
        (f"{ETC}/init.d", ["data/doorpi.sh"]),
        ("lib/systemd/system", ["data/doorpi.service", "data/doorpi.socket"]),
    ],
)