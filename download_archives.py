import argparse
import logging
import re
import tarfile
import tempfile
import time
import typing
from pathlib import Path
from textwrap import dedent

import requests

logger = logging.getLogger("archive-downloader")

logging.basicConfig(level=logging.INFO,format='%(message)s',datefmt='%Y-%m-%d %H:%M:%S')

perl_to_py_dict_regex = re.compile(r"(?P<key>\S*) (?P<value>[\s\S][^\n]*)")


def find_mirror() -> str:
    """Find a mirror and lock to it. Or else things could
    go weird."""
    # base_mirror = "http://mirror.ctan.org/systems/texlive/tlnet"
    # con = requests.get(base_mirror)
    # return con.history[-1].url
    # maybe let's try texlive.info
    timenow = time.localtime()
    return "https://texlive.info/tlnet-archive/%d/%02d/%02d/tlnet/" % (
        timenow.tm_year,
        timenow.tm_mon,
        timenow.tm_mday,
    )


def download_texlive_tlpdb(mirror: str) -> None:
    con = requests.get(mirror + "tlpkg/texlive.tlpdb")
    with open("texlive.tlpdb", "wb") as f:
        f.write(con.content)
    logger.info("Downloaded texlive.tlpdb")


def cleanup():
    logger.info("Cleaning up.")
    Path("texlive.tlpdb").unlink()


def parse_perl(perl_code) -> typing.Dict[str, typing.Union[list, str]]:
    final_dict: typing.Dict[str, typing.Union[list, str]] = {}
    for findings in perl_to_py_dict_regex.finditer(perl_code):
        key = findings.group("key")
        value = findings.group("value")
        if key:
            if key in final_dict:
                if isinstance(final_dict[key], str):
                    final_dict[key] = [final_dict[key], value]
                else:
                    final_dict[key].append(value)
            else:
                final_dict[key] = value
    return final_dict


def get_all_packages() -> typing.Dict[str, str]:
    with open("texlive.tlpdb", "r", encoding="utf-8") as f:
        lines = f.readlines()
    logger.info("Parsing texlive.tlpdb")
    package_list: typing.Dict[str, typing.Union[list, str]] = {}
    last_line = 0
    for n, line in enumerate(lines):
        if line == "\n":
            tmp = "".join(lines[last_line : n + 1]).strip()
            tmp_dict = parse_perl(tmp)
            name = tmp_dict["name"]
            if "." not in name:
                package_list[name] = tmp_dict
            last_line = n
    return package_list


def get_dependencies(
    name: str,
    pkglist: typing.Dict[str, str],
    collection_list: typing.List[str],
):
    pkg = pkglist[name]
    deps_list = []
    if "depend" not in pkg:
        return []
    for i in pkg["depend"]:
        dep_name = i
        if "collection" in dep_name or "scheme" in dep_name:
            if dep_name not in collection_list:
                collection_list.append(dep_name)
                deps_list += get_dependencies(dep_name, pkglist, collection_list)
        else:
            if dep_name not in deps_list:
                deps_list.append(dep_name)
    return deps_list


def get_needed_packages_with_info(scheme: str):
    logger.info("Resolving scheme %s", scheme)
    pkg_list = get_all_packages()
    deps = get_dependencies(scheme, pkg_list, [])
    deps.sort()
    deps_info = {}
    for i in deps:
        if "." not in i:
            deps_info[i] = pkg_list[i]
    return deps_info


def write_contents_file(mirror_url: str, pkgs: dict, file: Path):
    template = dedent(
        """\
    # These are the CTAN packages bundled in this package.
    # They were downloaded from {url}archive/
    # The svn revision number (on the TeXLive repository)
    # on which each package is based is given in the 2nd column.

    """
    ).format(url=mirror_url)
    for pkg in pkgs:
        template += f"{pkgs[pkg]['name']} {pkgs[pkg]['revision']}\n"
    with open(file, "w") as f:
        f.write(template)


def download(url, local_filename):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                # If you have chunk encoded response uncomment if
                # and set chunk_size parameter to None.
                # if chunk:
                f.write(chunk)


def download_and_retry(url: str, local_filename: Path):
    for i in range(10):
        logger.info("Downloading %s. Try: %s", url, i)
        try:
            download(url, local_filename)
            break
        except requests.HTTPError:
            pass
    else:
        raise Exception("%s can't be downloaded" % url)
    return True


def get_url_for_package(pkgname: str, mirror_url: str):
    if mirror_url[-1] == "/":
        return mirror_url + "archive/" + pkgname + ".tar.xz"
    return mirror_url + "/archive/" + pkgname + ".tar.xz"


def create_tar_archive(path: Path, output_filename: Path):
    logger.info("Creating tar file.")
    with tarfile.open(output_filename, "w:xz") as tar_handle:
        for f in path.iterdir():
            tar_handle.add(str(f), recursive=False, arcname=f.name)


def download_all_packages(scheme: str, mirror_url: str, final_tar_location: Path):
    logger.info("Starting to Download.")
    with tempfile.TemporaryDirectory() as tmpdir:
        logger.info("Using tempdir: %s", tmpdir)
        tmpdir = Path(tmpdir)
        needed_pkgs = get_needed_packages_with_info(scheme)
        write_contents_file(mirror_url, needed_pkgs, tmpdir / "CONTENTS")
        for pkg in needed_pkgs:
            logger.info("Downloading %s",needed_pkgs[pkg]["name"])
            url = get_url_for_package(needed_pkgs[pkg]["name"], mirror_url)
            file_name = tmpdir / Path(url).name
            download_and_retry(url, file_name)
        create_tar_archive(path=tmpdir, output_filename=final_tar_location)


def main(scheme, filename):
    mirror = find_mirror()
    logger.info("Using mirror: %s", mirror)
    download_texlive_tlpdb(mirror)
    # arch uses "scheme-medium"
    download_all_packages(scheme, mirror, filename)
    cleanup()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process some integers.")
    parser.add_argument("scheme", type=str, help="Scheme for which to Build archive.")
    parser.add_argument(
        "file_name", type=str, help="Full path to save the resultant file."
    )
    args = parser.parse_args()
    logger.info("Starting...")
    logger.info("Scheme: %s", args.scheme)
    logger.info("Filename: %s", args.file_name)
    main(args.scheme, args.file_name)
