#!/usr/bin/env python3

"""DoorPi Setup"""

from pathlib import Path
from os.path import basename, join, exists, expanduser
from os import chmod, makedirs, geteuid, getegid, execv
import sys
import subprocess
import importlib
from shutil import rmtree
from argparse import ArgumentParser

ap = ArgumentParser()
ap.add_argument("--prefix", required=False, help="prefix for setuptools setup")
ap.add_argument("install", help="build and install the package")
args = vars(ap.parse_args())

# base path of the cloned git
BASE_PATH = Path(__file__).resolve().parent
PACKAGE = basename(BASE_PATH)
PROJECT = PACKAGE.lower()
DEFAULT_PREFIX = join(expanduser("~"), ".local", "share")

PREFIX = args["prefix"] or DEFAULT_PREFIX
if PREFIX in ("/usr", "/usr/local"):
    WORKING_DIR = join(PREFIX, "etc", PROJECT)
else:
    WORKING_DIR = join(PREFIX, PROJECT)
CONFIG_DIR = join(WORKING_DIR, "conf")
CONFIG_FILE = join(CONFIG_DIR, f"{PROJECT}.ini")
LOG_FILE = join("/var", "log", PROJECT, f"{PROJECT}.log")
LOG_DIR = join("/var", "log", PROJECT)
# DAEMON_DIR = "/etc/init.d"


def pako_installed():
    def cleanup():
        if exists("/tmp/pako"):
            rmtree("/tmp/pako")

    proc_clone = subprocess.Popen(["git", "clone", "https://github.com/MycroftAI/pako"], cwd="/tmp")
    proc_clone.wait()
    if proc_clone.returncode != 0:
        cleanup()
        return False

    proc_setup = subprocess.Popen(["python3", "setup.py", "install"], cwd="/tmp/pako")
    proc_setup.wait()
    cleanup()
    if proc_setup.returncode != 0:
        return False

    return True


# Check for pip, setuptools and wheel
try:
    import pip
    import setuptools
    import wheel
except ImportError as exp:
    print("install missing pip now (%s)" % exp)
    from get_pip import main as check_for_pip

    old_args = sys.argv
    sys.argv = [sys.argv[0]]
    try:
        check_for_pip()
    except SystemExit as e:
        if e.code == 0:
            # Thus additional system packages are required, install a os independent packet manager (python package)
            if not pako_installed():
                print('''Exiting. Can't install the required packages. 
                Please install 'python3-pip' manually before installing DoorPi''')
                sys.exit()
            execv(sys.executable, [sys.executable] + old_args)
        else:
            print("install pip failed with error code %s" % e.code)
            sys.exit(e.code)

if importlib.util.find_spec("pako"):
    from pako import PakoManager
    manager = PakoManager()
    manager.update()
    manager.install(['python3-pip'], flags=['no-confirm'])

datapath = BASE_PATH / "data"
substkeys = {
    "package": PACKAGE,
    "project": PROJECT,
    "prefix": PREFIX,
    "cfgfile": CONFIG_FILE,
    "cfgdir": CONFIG_DIR,
    "logfile": LOG_FILE,
    "user": geteuid(),
    "group": getegid()
}

for file in datapath.iterdir():
    if file.suffix != ".in":
        continue
    content = file.read_text()
    for key, val in substkeys.items():
        content = content.replace(f"!!{key}!!", str(val))
    file.with_suffix("").write_text(content)
    # make the resulting file executable
    if file.stem.endswith(".sh"):
        chmod(join(datapath, file.stem), 0o755)

# create relevant folders
for folder in (CONFIG_DIR, LOG_DIR):
    if not exists(folder):
        makedirs(folder)
Path(CONFIG_FILE).touch()
if PREFIX != DEFAULT_PREFIX:
    with open(CONFIG_FILE, "w") as f:
        f.write(f'base_path = "{WORKING_DIR}"')


# system.d service used only until there's a need for it
# (DAEMON_DIR, ["data/doorpi.sh"]),
setuptools.setup(
    package_data={
        # include
        '': ['*.yml', '*.cfg', '*.txt', '*.toml', '*.rst', '*.wav', '*.ico', '*.md', '*.json', '*.html', '*.js',
             '*.css', '*.png', '*.tab', '*.sh', '*.gif', '*.jpg', '*.coffee', '*.less', '*.psd', '*.swf', '*.svg',
             '*.otf', '*.eot', '*.woff', '*.ttf', '*.scss', '*.db', '*.map', '*.lang', '*.xml', '*.pack', '*.idx',
             '*.sample'],
    },
    data_files=[
        # systemd service
        (join(PREFIX, "lib/systemd/system"), ["data/doorpi.service", "data/doorpi.socket"]),
    ],
)