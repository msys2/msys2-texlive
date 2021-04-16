import subprocess
from pathlib import Path

from .logger import logger
from .utils import check_whether_gpg_exists, find_checksum_from_file


def import_texlive_gpg_key():
    subprocess.run(
        ["gpg", "--import", str(Path(__file__).parent.resolve() / "texlive.asc")],
        cwd=Path(__file__).parent.resolve(),
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
