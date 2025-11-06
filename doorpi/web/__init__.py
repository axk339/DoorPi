"""The DoorPiWeb server"""
import asyncio
import http.server
import logging
import os
import pathlib
import socket
import threading
import typing as T

import doorpi
from doorpi.actions import CallbackAction

LOGGER: doorpi.DoorPiLogger = logging.getLogger(__name__)  # type: ignore

try:
    from . import server
except ImportError as err:
    _MISSING_DEP = err.name

    def load() -> T.Optional[threading.Thread]:  # pylint: disable=R1711
        """Load the webserver"""
        LOGGER.error(
            "Cannot start web server: Unmet dependencies: %s",
            _MISSING_DEP,
        )
        return None


else:

    _WEB_THREAD: T.Optional[threading.Thread] = None

    def load() -> T.Optional[threading.Thread]:
        """Load the webserver"""
        global _WEB_THREAD
        thread = threading.Thread(
            target=asyncio.run,
            args=(server.run(),),
            name="Webserver Thread",
        )
        eh = doorpi.INSTANCE.event_handler
        eh.register_event("OnWebServerStart", "doorpi.web")
        eh.register_event("OnWebServerStop", "doorpi.web")
        eh.register_action(
            "OnStartup", doorpi.actions.CallbackAction(thread.start)
        )
        
        # --- NEW Registration: Synchronous wait for thread cleanup ---
        eh.register_action(
            "OnShutdown", doorpi.actions.CallbackAction(shutdown)
        )
        
        _WEB_THREAD = thread
        return thread

    def shutdown() -> None:
        """
        Signals the web thread and then synchronously waits for it to complete cleanup.
        """
        global _WEB_THREAD
        
        # 1. NEW: Explicitly call the signaling function immediately
        signal_web_thread() 
        
        # 2. Synchronously wait for the web thread to join
        if _WEB_THREAD is not None and _WEB_THREAD.is_alive():
            LOGGER.info("Waiting for Webserver Thread to join (max 5s)...")
            
            # The join call now runs *after* the signal is guaranteed to be sent.
            _WEB_THREAD.join(timeout=5)
            
            if _WEB_THREAD.is_alive():
                LOGGER.warning("Webserver Thread did not terminate in time.")
            else:
                LOGGER.info("Webserver Thread successfully joined.")
        
        _WEB_THREAD = None

    # The new function to be called before the thread join
    def signal_web_thread() -> None:
        """
        Triggers the web thread's asynchronous shutdown sequence 
        by setting the asyncio.Event thread-safely.
        """
        
        if doorpi.web.server._WEB_LOOP and doorpi.web.server._SHUTDOWN_EVENT:
            try:
                LOGGER.info("Executing threadsafe signal to wake web thread.")
                # This is the core logic you wanted to move:
                doorpi.web.server._WEB_LOOP.call_soon_threadsafe(doorpi.web.server._SHUTDOWN_EVENT.set)
            except Exception as e:
                LOGGER.error(f"Failed to call threadsafe shutdown signal: {e}")
        else:
            LOGGER.warning("Web thread loop or event not initialized for signaling.")
