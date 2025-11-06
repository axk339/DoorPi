"""The server component of DoorPiWeb"""
import asyncio
import logging
import os
import socket
import typing as T

import aiohttp.web

import doorpi.metadata
# import doorpi.util
import doorpi.web.api
import doorpi.web.auth
import doorpi.web.resources

SD_LISTEN_FDS_START = 3  # defined in <systemd/sd-daemon.h>

logger = logging.getLogger(__name__)

RequestHandler = T.Callable[
    [aiohttp.web.Request], T.Awaitable[aiohttp.web.StreamResponse]
]

_WEB_LOOP: T.Optional[asyncio.AbstractEventLoop] = None
_SHUTDOWN_EVENT: T.Optional[asyncio.Event] = None

async def run() -> None:
    """Start the web server thread"""
    cfg = doorpi.INSTANCE.config.view("web")
    _ip = cfg["ip"]
    if _ip in ("0.0.0.0", "127.0.0.1"):
        _ip = socket.gethostbyname(socket.gethostname())
    shutdown = asyncio.Event()

    # Capture the loop that is running this coroutine
    web_loop = asyncio.get_running_loop() 

    # Add global variables to store the loop and event
    doorpi.web.server._WEB_LOOP = web_loop
    doorpi.web.server._SHUTDOWN_EVENT = shutdown
    
    app = aiohttp.web.Application()
    app["doorpi_web_config"] = cfg
    doorpi.web.resources.setup(app)
    app.add_routes(doorpi.web.api.routes)
    app.add_routes(doorpi.web.resources.routes)
    doorpi.web.auth.setup(app)
    runner = aiohttp.web.AppRunner(app, access_log=None)
    await runner.setup()

    fds = int(os.environ.get("LISTEN_FDS", "0"))
    if fds > 0:
        logger.debug("Received %d listen FDs", fds)
        for fd in range(SD_LISTEN_FDS_START, SD_LISTEN_FDS_START + fds):
            await aiohttp.web.SockSite(
                runner,
                socket.fromfd(fd, socket.AF_INET, socket.SOCK_STREAM),
            ).start()
    else:
        await aiohttp.web.TCPSite(runner, cfg["ip"], cfg["port"]).start()

    logger.info(f"webserver exposed at {_ip}:{cfg['port']}")

    eh = doorpi.INSTANCE.event_handler
    eh.fire_event_sync("OnWebServerStart", "doorpi.web")
    #eh.register_action(
    #    "OnShutdown",
    #    doorpi.actions.CallbackAction(
    #        web_loop.call_soon_threadsafe,
    #        shutdown.set,
    #    ),
    #)
    
    try:
        await shutdown.wait()
        logger.info("Webserver received shutdown signal. Starting cleanup...") # Log here
    finally:
        logger.info("Starting aiohttp runner shutdown and cleanup...")
        
        # 1. Explicitly stop listening and gracefully close connections
        # This function handles the graceful shutdown process.
        await runner.shutdown()
        
        # 2. Final cleanup of resources. NOTE: No 'timeout' argument here.
        await runner.cleanup() 
        
        doorpi.web.server.doorpi.web.server._WEB_LOOP = None
        doorpi.web.server._SHUTDOWN_EVENT = None
        
        # Unregistering the source should happen now
        eh.unregister_source("doorpi.web", force=True)
        logger.info("Webserver cleanup complete and source unregistered.")

