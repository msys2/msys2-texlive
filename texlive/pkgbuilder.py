# PKGBUILD for texlive-core and texlive-bin is different than others.

import re
import time
import typing
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape
from jinja2.environment import Template

from .constants import PACKAGE_COLLECTION
from .github_handler import Release
from .logger import logger
from .main import (
    download_texlive_tlpdb,
    find_mirror,
    get_all_packages,
)
from .requests_handler import retry_get

release = Release()


@dataclass
class PackageVersion:
    """A class representing the version to be set to
    packages.

    Attributes
    ==========
    major
        The major version
    minor
        The minor version
    """

    major: str
    minor: str


@dataclass
class Package:
    name: str
    desc: str
    # version: PackageVersion
    deps: typing.List[str]
    groups: typing.List[str]
    sha256sums: typing.List[str]  # ! should contain only 2 elements
    backup: typing.List[str]
    copy_extra_files: typing.List[typing.Tuple[str, str]]
    extra_cleanup_scripts_sed: typing.List[str]
    extra_cleanup_scripts_final: typing.List[
        str
    ]  # ! a list of exectuables without .exe


@dataclass
class JinjaHandler:
    environment: Environment = Environment(
        loader=PackageLoader("texlive", "recipes"),
        autoescape=select_autoescape((".jinjatemplate")),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    def get_template(self, template_type: str = "common") -> Template:
        """get_template Get the JinjaTemplate to render things.

        Parameters
        ----------
        template_type : str, optional
            Either "common","core","bin", which will point to
            each of the templates for the packages, by default "common"

        Returns
        -------
        Template
            The Jinja Template
        """
        if template_type == "bin":
            return self.environment.get_template("PKGBUILD-texlive-bin.jinjatemplate")
        elif template_type == "core":
            return self.environment.get_template("PKGBUILD-texlive-core.jinjatemplate")
        else:
            return self.environment.get_template("PKGBUILD-common.jinjatemplate")


def get_version() -> PackageVersion:
    return PackageVersion(
        major=time.strftime("%Y"),
        minor=release.version,
    )


def find_collection_dependencies(
    pkg_info: typing.Dict[str, typing.Union[str, list]]
) -> typing.Union[typing.List[str]]:
    def find_package_name_from_collection(col_name: str) -> typing.Union[str, None]:
        # I know this is dirty by no other better way :face_palm:
        for pkg_name, collection in PACKAGE_COLLECTION.items():
            if isinstance(collection, list):
                if col_name in collection:
                    return None
                continue
            if collection == col_name:
                return pkg_name
        else:
            raise Exception("No mapping.")

    if "depend" in pkg_info:
        deps = []
        for dep in pkg_info["depend"]:
            if dep.startswith("collection-"):
                p_dep = find_package_name_from_collection(dep)
                if p_dep:
                    deps.append(p_dep)
        return deps
    return []


def get_all_scheme(
    pkgs_info: typing.Dict[str, typing.Dict[str, typing.Union[list, str]]]
) -> typing.List[str]:
    schemes = []
    for pkg in pkgs_info:
        if pkg.startswith("scheme-"):
            schemes.append(pkg)
    return schemes


def get_groups(
    pkg: typing.Union[str, typing.List[str]],
    pkgs_info: typing.Dict[str, typing.Dict[str, typing.Union[list, str]]],
) -> typing.List[str]:
    """get_groups Get the groups to be added for the package

    Parameters
    ----------
    pkg : str
        The collection-name.
    pkgs_info : typing.Dict[str, typing.Dict[str, typing.Union[list, str]]]
        Full package details.

    Returns
    -------
    List[str]
        a list of strings of groups
    """
    # Now this is going to be resource heavy.
    # The plan is to create a list of schemes
    # and then get each of the deps of scheme
    # and then search for collection.
    groups = []
    schemes = get_all_scheme(pkgs_info)

    def append_group(_pkg):
        for scheme in schemes:
            if "depend" in pkgs_info[scheme]:
                for collection in pkgs_info[scheme]["depend"]:
                    if collection == _pkg:
                        if scheme not in groups:
                            groups.append(scheme)

    if isinstance(pkg, list):
        for _pkg in pkg:
            append_group(_pkg)
    else:
        append_group(pkg)
    return groups


def get_checksums(pkg: str) -> typing.List[str]:
    checksums = []  # order: 1. actual package 2. extra files
    body = release.body
    version = release.version
    checksums_regex_main = re.compile(
        fr"(?P<checksum>[a-zA-Z0-9]*)  ({pkg}-{version}\.tar\.xz)"
    )
    _match = checksums_regex_main.search(body)
    if _match:
        checksums.append(_match.group("checksum"))
    checksums_regex_extra = re.compile(
        fr"(?P<checksum>[a-zA-Z0-9]*)  ({pkg}-extra-files\.tar\.xz)"
    )
    _match = checksums_regex_extra.search(body)
    if _match:
        checksums.append(_match.group("checksum"))
    return checksums


def make_pkgbuild_for_texlive_bin(
    commit_version: str,
    jinja_handler: JinjaHandler,
    version_info: PackageVersion,
    repo_path: Path,
):
    template = jinja_handler.get_template("bin")
    final_scripts = []
    con_handler = retry_get(
        f"https://github.com/TeX-Live/texlive-source/raw/{commit_version}/texk/texlive/linked_scripts/scripts.lst"  # noqa: E501
    )
    contents = con_handler.text
    contents_lst = contents.split()[1:-1]
    for _bin in contents_lst:
        _final_bin = _bin.split("/")[-1].split(".")[0]
        final_scripts.append(_final_bin)
    final_result = template.render(
        version=version_info, cleanup_scripts_final=final_scripts
    )
    pkgbuild_location = repo_path / "mingw-w64-texlive-bin" / "PKGBUILD"
    if not pkgbuild_location.exists():
        pkgbuild_location.parent.mkdir()
    with pkgbuild_location.open("w", encoding="utf-8", newline="\n") as f:
        f.write(final_result)
    logger.info("Writtern PKGBUILD for texlive-bin")


def main(repo_path: Path, texlive_bin: bool = False, commit_version: str = None):
    if not Path("texlive.tlpdb").exists():
        download_texlive_tlpdb(find_mirror())
    jinja = JinjaHandler()
    version = get_version()
    if texlive_bin:
        assert commit_version is not None
        make_pkgbuild_for_texlive_bin(commit_version, jinja, version, repo_path)
    all_pkg = get_all_packages()
    for pkg in PACKAGE_COLLECTION:
        backup: typing.List[str] = []
        copy_extra_files: typing.List[typing.Tuple[str, str]] = []
        extra_cleanup_scripts_sed: typing.List[str] = []
        extra_cleanup_scripts_final: typing.List[str] = []
        if pkg == "texlive-core":
            package = Package(
                name=pkg,
                desc="TeX Live core distribution",
                deps=[],
                groups=get_groups(PACKAGE_COLLECTION[pkg], all_pkg),
                sha256sums=get_checksums(pkg),
                backup=backup,
                copy_extra_files=copy_extra_files,
                extra_cleanup_scripts_sed=extra_cleanup_scripts_sed,
                extra_cleanup_scripts_final=extra_cleanup_scripts_final,
            )
            template = jinja.get_template("core")
        else:
            if pkg == "texlive-extra-utils":
                backup.append("${MINGW_PREFIX:1}/etc/texmf/chktex/chktexrc")
                copy_extra_files.append(
                    (
                        "${pkgdir}${MINGW_PREFIX}/share/texmf-dist/chktex/chktexrc",
                        "${pkgdir}${MINGW_PREFIX}/etc/texmf/chktex/",
                    ),
                )
                # extra_cleanup_scripts_final.append("mflua")
            package = Package(
                name=pkg,
                desc=str(all_pkg[str(PACKAGE_COLLECTION[pkg])]["shortdesc"]),
                deps=find_collection_dependencies(
                    all_pkg[str(PACKAGE_COLLECTION[pkg])]
                ),
                groups=get_groups(PACKAGE_COLLECTION[pkg], all_pkg),
                sha256sums=get_checksums(pkg),
                backup=backup,
                copy_extra_files=copy_extra_files,
                extra_cleanup_scripts_sed=extra_cleanup_scripts_sed,
                extra_cleanup_scripts_final=extra_cleanup_scripts_final,
            )
            template = jinja.get_template()
        final_result = (
            template.render(package=package, version=version) + "\n"
        )  # add a new line as jinja strips it
        pkgbuild_location = repo_path / f"mingw-w64-{pkg}" / "PKGBUILD"
        if not pkgbuild_location.exists():
            pkgbuild_location.parent.mkdir()
        with pkgbuild_location.open("w", encoding="utf-8", newline="\n") as f:
            f.write(final_result)
