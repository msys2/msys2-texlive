import time
from pathlib import Path

import requests

from .constants import RETRY_INTERVAL
from .logger import logger

__all__ = ["find_mirror", "download", "download_and_retry"]


def find_mirror(texlive_info: bool = False) -> str:
    """Find a mirror and lock to it. Final fallback
    is texlive.info

    This is important because we shouldn't be changing mirrors
    randomly, rather we should fix to one which is working or
    fallback to.

    Parameters
    ----------
    texlive_info : bool, optional
        Whether to use http://texlive.info?, by default False

    Returns
    -------
    str
        The mirror URL which should point to ``tlnet`` folder
        in the mirror.
    """
    if not texlive_info:
        base_mirror = "https://mirror.ctan.org"
        con = retry_get(base_mirror)
        return con.url + "systems/texlive/tlnet/"

    # maybe let's try texlive.info
    timenow = time.localtime()
    url = "https://texlive.info/tlnet-archive/%d/%02d/%02d/tlnet/" % (
        timenow.tm_year,
        timenow.tm_mon,
        timenow.tm_mday,
    )
    con = retry_get(url)
    if con.status_code == 404:
        return "https://texlive.info/tlnet-archive/%d/%02d/%02d/tlnet/" % (
            timenow.tm_year,
            timenow.tm_mon,
            timenow.tm_mday - 1,
        )
    return url


def download(url: str, local_filename: Path):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)


def download_and_retry(url: str, local_filename: Path):
    logger.info("Downloading %s to %s", url, local_filename)
    for i in range(10):
        logger.info("Try: %s/10", i + 1)
        try:
            download(url, local_filename)
            break
        except (requests.HTTPError, requests.ConnectionError) as e:
            time.sleep(RETRY_INTERVAL)
            logger.debug(e)

    else:
        raise requests.HTTPError("%s can't be downloaded" % url)
    return True


def retry_get(url: str) -> requests.Response:
    logger.info("Getting %s.", url)
    for i in range(10):
        logger.info("Try: %s/10", i + 1)
        try:
            con = requests.get(url)
            break
        except (requests.HTTPError, requests.ConnectionError) as e:
            time.sleep(RETRY_INTERVAL)
            logger.debug(e)

    else:
        raise requests.HTTPError("%s can't be downloaded" % url)
    return con
