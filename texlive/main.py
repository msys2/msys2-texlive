"""

    download_archives.py
    ~~~~~~~~~~~~~~~~~~~~

    A utility to download required archives for texlive-packages
    by parsing `texlive.tlpdb` and creating `.fmts` and `.maps`
    from the parsed package. It downloads everything in directory
    specified and create a `.tar.xz` from them and uploades to
    Github Release. See `.github/workflows/build.yml` on how this
    works on Github Actions.

"""
import concurrent.futures
import shutil
import tempfile
import typing
from pathlib import Path

import requests

from .constants import perl_to_py_dict_regex
from .file_creator import create_fmts, create_maps
from .github_handler import upload_asset
from .logger import logger
from .requests_handler import download_and_retry, find_mirror
from .utils import (
    cleanup,
    create_tar_archive,
    get_file_archive_name,
    get_url_for_package,
    write_contents_file,
)
from .verify_files import check_sha512_sums, validate_gpg


def download_texlive_tlpdb(mirror: str) -> str:
    """This function download
    ``texlive.tlpdf`` from the :attr:mirror passed.
    This is later used in parsing and while downloading.

    Parameters
    ----------
    mirror : str
        The mirror URL.

    Returns
    -------
    str
        The mirror URL finally used.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tempdir = Path(tmpdir)
        temp_file = tempdir / "texlive.tlpdb"
        texlive_tlpdb = mirror + "tlpkg/texlive.tlpdb"
        texlive_tlpdb_sha512 = mirror + "tlpkg/texlive.tlpdb.sha512"
        texlive_tlpdb_sha512_asc = mirror + "tlpkg/texlive.tlpdb.sha512.asc"
        try:
            logger.info("Downloading texlive.tlpdb")
            download_and_retry(texlive_tlpdb, temp_file)
        except requests.HTTPError:
            logger.error("%s can't be downloaded" % texlive_tlpdb)
            logger.warning("Falling back to texlive.info")
            mirror = find_mirror(texlive_info=True)
            return download_texlive_tlpdb(mirror)
        logger.info("Downloaded texlive.tlpdb")

        file_to_check = tempdir / "texlive.tlpdb.sha512"
        signature_file = tempdir / "texlive.tlpdb.sha512.asc"
        download_and_retry(texlive_tlpdb_sha512, file_to_check)
        download_and_retry(texlive_tlpdb_sha512_asc, signature_file)
        validate_gpg(file_to_check, signature_file)

        with open(file_to_check, encoding="utf-8") as f:
            needed_sha512sum = f.read().split()[0]
        check_sha512_sums(temp_file, needed_sha512sum)
        shutil.copy(temp_file, Path("texlive.tlpdb"))
    return mirror


def parse_perl(perl_code) -> typing.Dict[str, typing.Union[list, str]]:
    final_dict: typing.Dict[str, typing.Union[list, str]] = {}
    for findings in perl_to_py_dict_regex.finditer(perl_code):
        key = findings.group("key")
        value = findings.group("value")
        if key:
            if key in final_dict:
                exists_value = final_dict[key]
                if isinstance(exists_value, str):
                    exists_value = [final_dict[key], value]
                else:
                    exists_value.append(value)
                final_dict[key] = exists_value
            else:
                final_dict[key] = value
    return final_dict


def get_all_packages() -> typing.Dict[str, typing.Dict[str, typing.Union[list, str]]]:
    with open("texlive.tlpdb", "r", encoding="utf-8") as f:
        lines = f.readlines()
    logger.info("Parsing texlive.tlpdb")
    package_list: typing.Dict[str, typing.Dict[str, typing.Union[list, str]]] = {}
    last_line: int = 0
    for n, line in enumerate(lines):
        if line == "\n":
            tmp = "".join(lines[last_line : n + 1]).strip()
            tmp_dict = parse_perl(tmp)
            name = str(tmp_dict["name"])
            package_list[name] = tmp_dict
            last_line = n
    return package_list


def get_dependencies(
    name: str,
    pkglist: typing.Dict[str, typing.Dict[str, typing.Union[list, str]]],
    collection_list: typing.List[str] = [],
    final_deps: typing.List[str] = [],
) -> typing.List[str]:
    if ".ARCH" in name:
        return []
    pkg: typing.Dict[str, typing.Union[list, str]] = pkglist[name]
    if "depend" not in pkg:
        return []
    dep_name = pkg["depend"]
    if isinstance(dep_name, str):
        if ".ARCH" in dep_name:
            return []
        if dep_name not in final_deps:
            final_deps.append(dep_name)
            get_dependencies(dep_name, pkglist, collection_list, final_deps)
        if "collection" in dep_name or "scheme" in dep_name:
            collection_list.append(dep_name)
            get_dependencies(dep_name, pkglist, collection_list, final_deps)
    else:
        for i in pkg["depend"]:
            dep_name = i
            if ".ARCH" in dep_name:
                continue
            if "collection" in dep_name or "scheme" in dep_name:
                if dep_name not in collection_list:
                    final_deps.append(dep_name)
                    collection_list.append(dep_name)
                    get_dependencies(dep_name, pkglist, collection_list, final_deps)
            else:
                if dep_name not in final_deps:
                    final_deps.append(dep_name)
                    get_dependencies(dep_name, pkglist, collection_list, final_deps)
    return final_deps


def get_needed_packages_with_info(
    scheme: str,
) -> typing.Dict[str, typing.Union[typing.Dict[str, typing.Union[str, list]]]]:
    logger.info("Resolving scheme %s", scheme)
    pkg_list = get_all_packages()
    deps = get_dependencies(scheme, pkg_list)
    deps.sort()
    deps_info = {}
    for i in deps:
        deps_info[i] = pkg_list[i]
    return deps_info


def download_all_packages(
    scheme: str,
    mirror_url: str,
    final_tar_location: Path,
    needed_pkgs: typing.Dict[
        str, typing.Union[typing.Dict[str, typing.Union[str, list]]]
    ],
):
    logger.info("Starting to Download.")

    def _internal_download(
        pkg: str,
        needed_pkgs: typing.Dict[
            str, typing.Union[typing.Dict[str, typing.Union[str, list]]]
        ],
        mirror_url: str,
        tmpdir: Path,
    ):
        logger.info("Downloading %s", needed_pkgs[pkg]["name"])
        url = get_url_for_package(str(needed_pkgs[pkg]["name"]), mirror_url)
        file_name = tmpdir / Path(url).name
        download_and_retry(url, file_name)
        needed_checksum = str(needed_pkgs[pkg]["containerchecksum"])
        check_sha512_sums(file_name, needed_checksum)

    with tempfile.TemporaryDirectory() as tmpdir_main:
        logger.info("Using tempdir: %s", tmpdir_main)
        tmpdir = Path(tmpdir_main)

        write_contents_file(mirror_url, needed_pkgs, tmpdir / "CONTENTS")
        # download with threads
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for pkg in needed_pkgs:
                executor.submit(
                    _internal_download,
                    pkg,
                    needed_pkgs,
                    mirror_url,
                    tmpdir,
                )
        create_tar_archive(path=tmpdir, output_filename=final_tar_location)


def main_laucher(scheme: str, directory: Path, package: str):
    """This is the main entrypoint

    This program will parse and download archives from
    CTAN which can be used while packaging texlive.

    Parameters
    ----------
    scheme : str
        The scheme or collection to search for. It can be
        anything which it available in ``texlive.tlpsrc``.
    directory : Path
        The directory to save files downloaded.
    package : str
        The package name you are packaging. It will be used
        in file name.
    """
    try:
        mirror = find_mirror()
        logger.info("Using mirror: %s", mirror)
        mirror = download_texlive_tlpdb(mirror)

        needed_pkgs = get_needed_packages_with_info(scheme)
        archive_name = directory / get_file_archive_name(package)

        logger.info("Number of needed Packages: %s", len(needed_pkgs))

        # arch uses "scheme-medium" for texlive-core
        download_all_packages(scheme, mirror, archive_name, needed_pkgs)
        logger.info("Uploading %s", archive_name)
        upload_asset(archive_name)  # uploads archive
    except requests.HTTPError as e:
        logger.error("Failed with: %s", e)
        logger.warning("Retrying with texlive.info")
        mirror = find_mirror(texlive_info=True)
        logger.info("Using mirror: %s", mirror)
        mirror = download_texlive_tlpdb(mirror)

        needed_pkgs = get_needed_packages_with_info(scheme)
        archive_name = directory / get_file_archive_name(package)

        logger.info("Number of needed Packages: %s", len(needed_pkgs))

        # arch uses "scheme-medium" for texlive-core
        download_all_packages(scheme, mirror, archive_name, needed_pkgs)
        logger.info("Uploading %s", archive_name)
        upload_asset(archive_name)  # uploads archive
    fmts_file = directory / (package + ".fmts")
    create_fmts(needed_pkgs, fmts_file)
    logger.info("Uploading %s", fmts_file)
    upload_asset(fmts_file)

    maps_file = directory / (package + ".maps")
    create_maps(needed_pkgs, maps_file)
    logger.info("Uploading %s", maps_file)
    upload_asset(maps_file)

    cleanup()
