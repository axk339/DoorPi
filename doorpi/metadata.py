"""Additional project metadata"""
# pylint: disable=invalid-name

from importlib import metadata as _meta

try:
    distribution = _meta.distribution(__name__.split(".")[0])
except _meta.PackageNotFoundError:  # pragma: no cover
    raise RuntimeError("DoorPi was not properly installed") from None

project = "VoIP Door-Intercomstation with Raspberry Pi"

supporters = (
    "Phillip Munz <office@businessaccess.info>",
    "Hermann Dötsch <doorpi1@gmail.com>",
    "Dennis Häußler <haeusslerd@outlook.com>",
    "Hubert Nusser <hubsif@gmx.de>",
    "Michael Hauer <frrr@gmx.at>",
    "Andreas Schwarz <doorpi@schwarz-ketsch.de>",
    "Max Rößler <max_kr@gmx.de>",
)
coauthor = (
    "emphasis: https://github.com/emphasize",
    "Wüstengecko: https://github.com/Wuestengecko",
    "motom001: https://github.com/motom001",
)

# created with: http://patorjk.com/software/taag/#p=display&f=Ogre&t=DoorPi
epilog = r"""
    ___                  ___ _
   /   \___   ___  _ __ / _ (_)  {project}
  / /\ / _ \ / _ \| '__/ /_)/ |  Version:   {version}
 / /_// (_) | (_) | | / ___/| |  License:   {license}
/___,' \___/ \___/|_| \/    |_|  URL:       {url}

Author:     {author}
Fork from:  {coauthor}
Supporter:  {supporters}
""".format(
    license=distribution.metadata["License"],
    project=distribution.metadata["Name"],
    version=distribution.metadata["Version"],
    author="{}: {}".format(
        distribution.metadata["Author"], distribution.metadata["Author-email"]
    ),
    coauthor="\n            ".join(coauthor),
    supporters="\n            ".join(supporters),
    url=distribution.metadata["Home-page"],
)
