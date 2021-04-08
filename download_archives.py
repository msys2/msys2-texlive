import argparse
import concurrent.futures
import logging
import re
import tarfile
import tempfile
import time
import typing
from pathlib import Path
from textwrap import dedent

import requests

from github_handler import upload_asset

logger = logging.getLogger("archive-downloader")

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="%Y-%m-%d-%H:%M:%S",
)

perl_to_py_dict_regex = re.compile(r"(?P<key>\S*) (?P<value>[\s\S][^\n]*)")
RETRY_INTERVAL = 10  # in seconds
PACKAGE_COLLECTION = {
    "texlive-core": "scheme-medium",
    "texlive-bibtexextra": "collection-bibtexextra",
    "texlive-fontsextra": "collection-fontsextra",
    "texlive-formatsextra": "collection-formatsextra",
    "texlive-games": "texlive-games",
    "texlive-humanities": "collection-humanities",
    "texlive-langchinese": "collection-langchinese",
    "texlive-langcyrillic": "collection-langcyrillic",
    "texlive-langextra": "collection-langextra",
    "texlive-langgreek": "collection-langgreek",
    "texlive-langjapanese": "collection-langjapanese",
    "texlive-langkorean": "collection-langkorean",
    "texlive-latexextra": "collection-latexextra",
    "texlive-music": "collection-music",
    "texlive-pictures": "collection-pictures",
    "texlive-pstricks": "collection-pstricks",
    "texlive-publishers": "collection-publishers",
    "texlive-science": "collection-science",
}


def find_mirror(texlive_info: bool = False) -> str:
    """Find a mirror and lock to it. Or else things could
    go weird."""
    if not texlive_info:
        base_mirror = "http://mirror.ctan.org"
        con = requests.get(base_mirror)
        return con.url + "systems/texlive/tlnet/"

    # maybe let's try texlive.info
    timenow = time.localtime()
    url = "https://texlive.info/tlnet-archive/%d/%02d/%02d/tlnet/" % (
        timenow.tm_year,
        timenow.tm_mon,
        timenow.tm_mday,
    )
    con = requests.get(url)
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
                # If you have chunk encoded response uncomment if
                # and set chunk_size parameter to None.
                # if chunk:
                f.write(chunk)


def download_and_retry(url: str, local_filename: Path):
    for i in range(10):
        logger.info("Downloading %s.", url)
        logger.info("Try: %s", i)
        try:
            download(url, local_filename)
            break
        except (requests.HTTPError, requests.ConnectionError) as e:
            time.sleep(RETRY_INTERVAL)
            logger.debug(e)

    else:
        raise requests.HTTPError("%s can't be downloaded" % url)
    return True


def get_file_archive_name(package: str) -> str:
    version = time.strftime("%Y%m%d")
    return f"{package}-{version}.tar.xz"


def download_texlive_tlpdb(mirror: str) -> str:
    url = mirror + "tlpkg/texlive.tlpdb"
    try:
        logger.info("Downloading texlive.tlpdb")
        download_and_retry(url, Path("texlive.tlpdb"))
    except requests.HTTPError:
        logger.error("%s can't be downloaded" % url)
        logger.warning("Falling back to texlive.info")
        mirror = find_mirror(texlive_info=True)
        return download_texlive_tlpdb(mirror)
    logger.info("Downloaded texlive.tlpdb")
    return mirror


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


def get_url_for_package(pkgname: str, mirror_url: str):
    if mirror_url[-1] == "/":
        return mirror_url + "archive/" + pkgname + ".tar.xz"
    return mirror_url + "/archive/" + pkgname + ".tar.xz"


def create_tar_archive(path: Path, output_filename: Path):
    logger.info("Creating tar file.")
    with tarfile.open(output_filename, "w:xz") as tar_handle:
        for f in path.iterdir():
            tar_handle.add(str(f), recursive=False, arcname=f.name)


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


def create_fmts(
    pkg_infos: typing.Dict[
        str, typing.Union[typing.Dict[str, typing.Union[str, list]]]
    ],
    filename_save: Path,
) -> Path:
    logger.info("Creating %s file", filename_save)
    key_value_search_regex = re.compile(r"(?P<key>\S*)=(?P<value>[\S]+)")
    quotes_search_regex = re.compile(
        r"((?<![\\])['\"])(?P<options>(?:.(?!(?<![\\])\1))*.?)\1"
    )
    final_file = ""

    def parse_perl_string(temp: str) -> typing.Dict[str, str]:
        t_dict: typing.Dict[str, str] = {}
        for mat in key_value_search_regex.finditer(temp):
            if '"' not in mat.group("value"):
                t_dict[mat.group("key")] = mat.group("value")
        quotes_search = quotes_search_regex.search(temp)
        if quotes_search:
            t_dict["options"] = quotes_search.group("options")
        for i in {"name", "engine", "patterns", "options"}:
            if i not in t_dict:
                t_dict[i] = "-"
        return t_dict

    for pkg in pkg_infos:
        temp_pkg = pkg_infos[pkg]
        if "execute" in temp_pkg:
            temp = temp_pkg["execute"]
            if isinstance(temp, str):
                if "AddFormat" in temp:
                    parsed_dict = parse_perl_string(temp)
                    final_file += "{name} {engine} {patterns} {options}\n".format(
                        **parsed_dict
                    )
            else:
                for each in temp:
                    if "AddFormat" in each:
                        parsed_dict = parse_perl_string(each)
                        final_file += "{name} {engine} {patterns} {options}\n".format(
                            **parsed_dict
                        )
    with filename_save.open("w", encoding="utf-8") as f:
        f.write(final_file)
        logger.info("Wrote %s", filename_save)
    return filename_save


def create_maps(
    pkg_infos: typing.Dict[
        str, typing.Union[typing.Dict[str, typing.Union[str, list]]]
    ],
    filename_save: Path,
) -> Path:
    logger.info("Creating %s file", filename_save)
    final_file = ""

    kanji_map_regex = re.compile(r"add(?P<final>KanjiMap[\s\S][^\n]*)")
    mixed_map_regex = re.compile(r"add(?P<final>MixedMap[\s\S][^\n]*)")
    map_regex = re.compile(r"add(?P<final>Map[\s\S][^\n]*)")

    def parse_string(temp: str):
        if "addMixedMap" in temp:
            res = mixed_map_regex.search(temp)
            if res:
                return res.group("final")
        elif "addMap" in temp:
            res = map_regex.search(temp)
            if res:
                return res.group("final")
        elif "addKanjiMap" in temp:
            res = kanji_map_regex.search(temp)
            if res:
                return res.group("final")

    for pkg in pkg_infos:
        temp_pkg = pkg_infos[pkg]
        if "execute" in temp_pkg:
            temp = temp_pkg["execute"]
            if isinstance(temp, str):
                if "addMap" in temp or "addMixedMap" in temp or "addKanjiMap" in temp:
                    final_file += parse_string(temp)
                    final_file += "\n"
            else:
                for each in temp:
                    if (
                        "addMap" in each
                        or "addMixedMap" in each
                        or "addKanjiMap" in each
                    ):
                        final_file += parse_string(each)
                        final_file += "\n"

    # let's sort the line
    temp_lines = final_file.split("\n")
    temp_lines.sort()
    final_file = "\n".join(temp_lines)
    final_file.strip()
    with filename_save.open("w", encoding="utf-8") as f:
        f.write(final_file)
        logger.info("Wrote %s", filename_save)
    return filename_save


def main(scheme: str, directory: Path, package: str):
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

    fmts_file = directory / (package + ".fmts")
    create_fmts(needed_pkgs, fmts_file)
    logger.info("Uploading %s", fmts_file)
    upload_asset(fmts_file)

    maps_file = directory / (package + ".maps")
    create_maps(needed_pkgs, maps_file)
    logger.info("Uploading %s", maps_file)
    upload_asset(maps_file)

    cleanup()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process some integers.")
    parser.add_argument(
        "package",
        type=str,
        help="Tha pacakge to build.",
        choices=PACKAGE_COLLECTION.keys(),
    )
    parser.add_argument("directory", type=str, help="The directory to save files.")
    args = parser.parse_args()
    logger.info("Starting...")
    logger.info("Package: %s", args.package)
    logger.info("Directory: %s", args.directory)

    if args.package in PACKAGE_COLLECTION:
        main(PACKAGE_COLLECTION[args.package], Path(args.directory), args.package)
