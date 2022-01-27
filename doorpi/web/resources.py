"""DoorPiWeb handlers for resources"""
import logging
from os import environ
from os.path import normpath
from pathlib import Path, PurePosixPath, PurePath
from urllib.parse import unquote
from sys import platform
from typing import Union

import aiohttp.web
import aiohttp_jinja2
import jinja2

import doorpi
#import doorpi.metadata
from . import templates

routes = aiohttp.web.RouteTableDef()
logger = logging.getLogger(__name__)
parsable_file_extensions = {".html"}


def setup(app: aiohttp.web.Application) -> None:
    """Setup the aiohttp_jinja2 environment"""
    if platform == "linux":
        try:
            cachedir = Path(environ["XDG_CACHE_HOME"])
        except KeyError:
            cachedir = Path.home() / ".cache"
    elif platform == "win32":
        cachedir = Path(environ["TEMP"])
    else:
        cachedir = Path.home()
    cachedir /= doorpi.metadata.distribution.metadata["Name"]
    cachedir /= "templatecache"
    cachedir.mkdir(parents=True, exist_ok=True)

    aiohttp_jinja2.setup(
        app,
        loader=templates.DoorPiWebTemplateLoader(),
        bytecode_cache=jinja2.FileSystemBytecodeCache(cachedir),
        undefined=jinja2.StrictUndefined,
        enable_async=True,
    )


@routes.get("/{path:$|.+}")
async def _resource(
    request: aiohttp.web.Request,
) -> aiohttp.web.StreamResponse:
    custom_paths = {doorpi.INSTANCE.config["snapshots.directory"],
                    doorpi.INSTANCE.config["base_path"]}

    if request.path == "/":
        cfg = doorpi.INSTANCE.config.view("web")
        request = request.clone(rel_url=str(cfg["indexpage"]))
    path = PurePosixPath(unquote(request.path))
    # is this a resource on a custom path? (ie screenshots,...)
    if normpath(path.parent) in [normpath(x) for x in custom_paths]:
        return await _custom_path_resource(path)
    elif path.suffix in parsable_file_extensions:
        return await _resource_template(request)
    else:
        resource = templates.get_resource(path)
        return aiohttp.web.Response(body=resource[0], content_type=resource[1])


async def _resource_template(
    request: aiohttp.web.Request,
) -> aiohttp.web.StreamResponse:
    return await aiohttp_jinja2.render_template_async(
        request.path,
        request,
        {
            "doorpi": doorpi.INSTANCE,
            "metadata": doorpi.metadata.distribution.metadata,
            "params": request.query,
            "code_min": ("", ".min")[
                logger.getEffectiveLevel() <= logging.DEBUG
            ],
            "proginfo": "{} - version: {}".format(
                doorpi.metadata.distribution.metadata["Name"],
                doorpi.metadata.distribution.metadata["Version"],
            ),
        },
    )


async def _custom_path_resource(path: Union[str, PurePosixPath]) -> aiohttp.web.FileResponse:
    # this is a relative path (based on base_path)
    if not str(path.parent).startswith("/"):
        path = PurePath(doorpi.INSTANCE.config["base_path"], path)

    return aiohttp.web.FileResponse(str(path))