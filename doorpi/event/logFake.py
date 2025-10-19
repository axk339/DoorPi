import logging
from typing import Any, Mapping, Optional, Tuple, TypedDict

LOGGER = logging.getLogger(__name__)


class EventLogEntry(TypedDict):
    event_id: str
    fired_by: str
    event_name: str
    start_time: float
    additional_infos: str


class EventLog:
    """Record keeper about fired events and executed actions"""

    def __init__(self, db: str) -> None:
        LOGGER.info("logging events to logger, skipping eventLogDB")

    def count_event_log_entries(self, filter_: str = "") -> int:
    	return 0

    def get_event_log(
        self,
        max_count: int = 100,
        filter_: str = "",
    ) -> Tuple[EventLogEntry, ...]:
        return ()

    def log_event(
        self,
        event_id: str,
        source: str,
        event: str,
        start_time: float,
        extra: Optional[Mapping[str, Any]],
    ) -> None:
        LOGGER.trace ("skipping log_event")
        LOGGER.debug ("["+event_id+"] ##EVENT## "+source+" >> "+event)

    def log_action(
        self, event_id: str, action_name: str, start_time: float
    ) -> None:
        LOGGER.trace ("skipping log_action")

    def destroy(self) -> None:
    	LOGGER.trace ("skipping destroy")
