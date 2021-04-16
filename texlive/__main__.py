import argparse
from pathlib import Path

from .constants import PACKAGE_COLLECTION
from .logger import logger
from .main import main_laucher

parser = argparse.ArgumentParser(description="Prepare texlive archives.")
parser.add_argument(
    "package",
    type=str,
    help="The pacakge to build.",
    choices=PACKAGE_COLLECTION.keys(),
)
parser.add_argument("directory", type=str, help="The directory to save files.")
args = parser.parse_args()
logger.info("Starting...")
logger.info("Package: %s", args.package)
logger.info("Directory: %s", args.directory)


main_laucher(PACKAGE_COLLECTION[args.package], Path(args.directory), args.package)
