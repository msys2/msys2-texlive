import subprocess
import tempfile
from pathlib import Path

from .constants import TEXLIVE_GPG_PUBLIC_KEY_URL
from .logger import logger
from .requests_handler import download
from .utils import check_whether_gpg_exists, find_checksum_from_file


def import_texlive_gpg_key():
    with tempfile.TemporaryDirectory() as tempdir:
        download(TEXLIVE_GPG_PUBLIC_KEY_URL, Path(tempdir) / "texlive.gpg")
        subprocess.run(
            ["gpg", "--import", str(Path(tempdir) / "texlive.gpg")],
            cwd=tempdir,
            check=True,
        )


def intialise_gpg():
    if check_whether_gpg_exists():
        import_texlive_gpg_key()
        return True
    return False


def validate_gpg(file: Path, signature: Path):
    """validate_gpg Check if a file and it's signature is valid.

    Parameters
    ----------
    file : Path
        The file to check.
    signature : Path
        The signature file(``.asc``)
    """
    if intialise_gpg():
        subprocess.run(
            [
                "gpg",
                "--verify",
                str(signature.absolute()),
                str(file.absolute()),
            ],
            check=True,
        )
    else:
        logger.warning("Can't find gpg. Not using it.")


def check_sha512_sums(file: Path, required_checksum: str):
    got_sha512sums = find_checksum_from_file(file, "sha512")
    assert got_sha512sums == required_checksum
