import logging

logger = logging.getLogger("archive-downloader")

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="%Y-%m-%d-%H:%M:%S",
)
