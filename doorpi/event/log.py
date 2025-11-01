import json
import logging
import pathlib
import sqlite3
from typing import Any, Mapping, Optional, Tuple, TypedDict

import os

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
        if not sqlite3.threadsafety:
            raise RuntimeError(
                "Your version of SQLite is not compiled thread-safe!"
            )

        dbpath = pathlib.Path(db)
        dbpath.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = str(dbpath)
        self._db = sqlite3.connect(
            database=str(self._db_path),
            timeout=1,
            isolation_level=None,
            check_same_thread=False,
        )

        with self._db:
            self._db.executescript(
                """
                CREATE TABLE IF NOT EXISTS event_log (
                    event_id TEXT,
                    fired_by TEXT,
                    event_name TEXT,
                    start_time REAL,
                    additional_infos TEXT
                );
                CREATE TABLE IF NOT EXISTS action_log (
                    event_id TEXT,
                    action_name TEXT,
                    start_time REAL,
                    action_result TEXT
                );
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY ON CONFLICT REPLACE,
                    value TEXT
                );
                INSERT INTO metadata VALUES ('db_version', '1');
                """
            )
    
    def clean (self) -> None:
        try:
            with self._db:
                # 1. Count the number of entries
                count_cursor = self._db.execute(
                    "SELECT COUNT(*) FROM event_log"
                )
                current_count = count_cursor.fetchone()[0]
                
                # 2. If count > 100, delete the oldest entry
                if current_count >= 100:
                    LOGGER.info(
                        "Event log has %d entries. Deleting oldest entry to cap size.",
                        current_count
                    )
                    # Delete the entry with the minimum start_time (the oldest event)
                    self._db.execute(
                        """
                        DELETE FROM event_log
                        WHERE start_time = (SELECT MIN(start_time) FROM event_log)
                        """
                    )

                # 3.vacuum db
                size_before_bytes = os.path.getsize(self._db_path)
                self._db.execute("VACUUM")
                size_after_bytes = os.path.getsize(self._db_path)
                LOGGER.info(f"Executing VACUUM, file size {size_before_bytes / 1024:.2f}kB > {size_after_bytes / 1024:.2f}kB")
                
        except Exception:
            LOGGER.exception("Error cleaning db")
    
    def count_event_log_entries(self, filter_: str = "") -> int:
        """Count the event log entries that match ``filter_``

        Args:
            filter_: A SQLite LIKE substring to filter any column
        """
        try:
            return self._db.execute(
                """
                SELECT COUNT(*) FROM event_log
                WHERE event_id LIKE ?
                OR fired_by LIKE ?
                OR event_name LIKE ?
                OR start_time LIKE ?
            """,
                (f"%{filter_}%",) * 4,
            ).fetchone()[0]
        except sqlite3.Error:
            LOGGER.exception(
                "Error counting event log with filter %r", filter_
            )
            return -1

    def get_event_log(
        self,
        max_count: int = 100,
        filter_: str = "",
    ) -> Tuple[EventLogEntry, ...]:
        """Get event records from the event log

        Args:
            max_count: The maximum number of events to fetch
            filter_: A SQLite LIKE substring to filter any column

        Returns:
            A tuple of dicts describing logged events.
            Each dict contains the following keys:

            * ``event_id``: The unique ID for this event.
            * ``fired_by``: The source that fired the event.
            * ``event_name``: The event name.
            * ``start_time``: The timestamp when the event fired.
            * ``additional_infos``: A JSON object with auxiliary info.
        """
        try:
            cursor = self._db.execute(
                """
                SELECT
                    event_id,
                    fired_by,
                    event_name,
                    start_time,
                    additional_infos
                FROM event_log
                WHERE event_id LIKE ?
                OR fired_by LIKE ?
                OR event_name LIKE ?
                OR start_time LIKE ?
                ORDER BY start_time ASC
                LIMIT ?""",
                (f"%{filter_}%",) * 4 + (max_count,),
            )

            return tuple(
                EventLogEntry(
                    {
                        "event_id": row[0],
                        "fired_by": row[1],
                        "event_name": row[2],
                        "start_time": row[3],
                        "additional_infos": row[4],
                    }
                )
                for row in cursor
            )
        except sqlite3.Error:
            LOGGER.exception("Error reading event log with filter %r", filter_)
            return ()

    def log_event(
        self,
        event_id: str,
        source: str,
        event: str,
        start_time: float,
        extra: Optional[Mapping[str, Any]],
    ) -> None:
        """Insert an event into the event log

        Args:
            event_id: The unique ID for this event
            source: The source that fired the event
            event: The event name
            start_time: The timestamp when the event fired
            extra: A JSON-serializable object with auxiliary info
        """
        try:
            with self._db:
                # 1. Count the number of entries
                count_cursor = self._db.execute(
                    "SELECT COUNT(*) FROM event_log"
                )
                current_count = count_cursor.fetchone()[0]
                
                # 2. If count > 100, delete the oldest entry
                if current_count >= 100:
                    LOGGER.debug(
                        "Event log has %d entries. Deleting oldest entry to cap size.",
                        current_count
                    )
                    # Delete the entry with the minimum start_time (the oldest event)
                    self._db.execute(
                        """
                        DELETE FROM event_log
                        WHERE start_time = (SELECT MIN(start_time) FROM event_log)
                        """
                    )

                # 3. Insert the new event
                self._db.execute(
                    "INSERT INTO event_log VALUES (?, ?, ?, ?, ?)",
                    (
                        event_id,
                        source,
                        event,
                        start_time,
                        json.dumps(extra, sort_keys=True) if extra else "",
                    ),
                )
        except sqlite3.Error:
            LOGGER.exception(
                "[%s] Cannot insert event %s into event log", event_id, event
            )

    def log_action(
        self, event_id: str, action_name: str, start_time: float
    ) -> None:
        """Insert an executed action into the event log

        Args:
            event_id: The unique ID of the associated event
            action_name: The configuration name of this action
            start_time: The timestamp when this action was executed
        """
        
        LOGGER.trace ("skipping log_action: " + action_name)
        
        #try:
        #    with self._db:
        #        self._db.execute(
        #            "INSERT INTO action_log VALUES (?, ?, ?, ?)",
        #            (event_id, action_name, start_time, ""),
        #        )
        #except sqlite3.Error:
        #    LOGGER.exception(
        #        "[%s] Cannot insert action %s into event log",
        #        event_id,
        #        action_name,
        #    )

    def destroy(self) -> None:
        """Shut down the event log"""
        self._db.close()
