"""Actions that perform requests to third party servers: http_request"""
import logging
import urllib.parse
from typing import Any, Mapping

import requests

from . import Action

LOGGER = logging.getLogger(__name__)

ALLOWED_SCHEMES = {"http", "https"}


class HTTPRequestAction(Action):
    """Performs a GET request to the given URL."""

    def __init__(self, *args: str) -> None:
        super().__init__()
        self.__url = ",".join(args)
        url = urllib.parse.urlparse(self.__url)
        if not url.scheme or not url.netloc:
            raise ValueError(f"Invalid URL: {url!r}")

        if url.scheme not in ALLOWED_SCHEMES:
            raise ValueError(f"Invalid scheme: {url.scheme}")

    def __call__(self, event_id: str, extra: Mapping[str, Any]) -> None:
        try:
            resp = requests.get(self.__url, timeout=2)
            LOGGER.info("Request '%s': Server response: %d %s", self.__url, resp.status_code, resp.reason)
        except requests.exceptions.Timeout:
            LOGGER.warning("Request '%s': Server request timed out", self.__url)
        
    def __str__(self) -> str:
        return f"HTTP Request to {self.__url}"

    def __repr__(self) -> str:
        return f"http_request:{self.__url}"
