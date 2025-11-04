"""Actions related to taking snapshots: snap_url, snap_picam"""
# pylint: disable=import-outside-toplevel

import sys
import datetime
import subprocess
import logging
import pathlib
from urllib.parse import urlparse
from typing import Any, List, Mapping

import doorpi

from . import Action

LOGGER = logging.getLogger(__name__)
DOORPI_SECTION = "DoorPi"


class SnapshotAction(Action):
    """Base class for snapshotting actions."""

    @classmethod
    def cleanup(cls) -> None:
        """Cleans out the snapshot directory

        The oldest snapshots are deleted until the directory only
        contains as many snapshots as set in the configuration.
        """

        keep = doorpi.INSTANCE.config["snapshots.keep"]
        if keep == 0:
            return
        files = cls.list_all()
        for fi in files[0:-keep]:
            try:
                LOGGER.info("Deleting old snapshot %s", fi)
                fi.unlink()
            except OSError:
                LOGGER.exception("Could not clean up snapshot %s", fi.name)

    @staticmethod
    #def get_base_path() -> pathlib.Path:
    def get_full_path() -> pathlib.Path:
        """Fetches the snapshot directory path from the configuration."""

        path = doorpi.INSTANCE.config["snapshots.directory"]
        if not path:
            raise ValueError("snapshot_path must not be empty")
        #add year folder for snapshot
        #path = pathlib.Path(path)
        year = datetime.datetime.now().strftime("%Y")
        path = pathlib.Path(path, year)
        if not str(path.parent).startswith("/"):
            path = pathlib.Path(doorpi.INSTANCE.base_path, path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def get_resolution() -> str:
        """Fetches the snapshot resolution from the configuration."""

        width = doorpi.INSTANCE.config["snapshots.width"]
        return width or None

    @classmethod
    def get_next_path(cls) -> pathlib.Path:
        """Computes the next snapshot's path."""

        path = cls.get_full_path() / datetime.datetime.now().strftime(
            #Replace : with -
            #"%Y-%m-%d_%H:%M:%S.jpg"
            "%Y-%m-%d_%H-%M-%S.jpg"
        )
        return path

    @classmethod
    def list_all(cls) -> List[pathlib.Path]:
        """Lists all snapshot files in the snapshot directory."""
        return sorted(f for f in cls.get_full_path().iterdir() if f.is_file())


class URLSnapshotAction(SnapshotAction):
    """Fetches a URL and saves it as snapshot."""

    def __init__(self, url: str) -> None:
        import requests

        super().__init__()

        self.__url = url

    def __call__(self, event_id: str, extra: Mapping[str, Any]) -> None:
        import requests

        try:
            response = requests.get(self.__url, stream=True)
            with self.get_next_path().open("wb") as output:
                for chunk in response.iter_content(1048576):  # 1 MiB chunks
                    output.write(chunk)
        except Exception as e:
            LOGGER.error(f"Can't make a snapshot: {str(e)}")

        self.cleanup()

    def __str__(self) -> str:
        return f"Save the image from {self.__url} as snapshot"

    def __repr__(self) -> str:
        return f"snap_url:{self.__url}"


class StreamSnapshotAction(SnapshotAction):
    """Converts a snapshot from a webcam stream (that has not yet an API for it) and saves it."""

    def __init__(self, url: str, width: str = None) -> None:

        super().__init__()

        self.__url = urlparse(url)
        self.width = width or self.get_resolution()

    def __call__(self, event_id: str, extra: Mapping[str, Any]) -> None:
        import ffmpeg

        __outfile = str(self.get_next_path())
        try:
            (
            ffmpeg
                .input(self.__url.geturl())
                .filter('scale', self.width or -1, -1)
                .output(__outfile, vframes=1)
                .overwrite_output()
                .run_async(pipe_stdin=subprocess.DEVNULL, pipe_stdout=True, pipe_stderr=True)
            )
        except ffmpeg.Error as e:
            LOGGER.error(f"Can't make a snapshot: {e.stderr.decode()}")
        else:
            LOGGER.info(f"Snapshot saved at: {__outfile}")

        self.cleanup()

    def __str__(self) -> str:
        return f"Save the image from {self.__url} as snapshot"

    def __repr__(self) -> str:
        return f"snap_stream:{self.__url}"


class PicamSnapshotAction(SnapshotAction):
    """Takes a snapshot from the Pi Camera."""

    def __init__(self) -> None:
        super().__init__()
        # Make sure picamera is importable
        import picamera  # pylint: disable=import-error, unused-import

    def __call__(self, event_id: str, extra: Mapping[str, Any]) -> None:
        import picamera  # pylint: disable=import-error

        with picamera.PiCamera() as cam:
            cam.resolution = (1024, 768)
            cam.capture(self.get_next_path())

        self.cleanup()

    def __str__(self) -> str:
        return "Take a snapshot from the Pi Camera"

    def __repr__(self) -> str:
        return "snap_picam:"