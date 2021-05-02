# PKGBUILD for texlive-core and texlive-bin is different than others.

import re
import time
import typing
from dataclasses import dataclass

from jinja2 import Environment, PackageLoader, select_autoescape
from jinja2.environment import Template

from .constants import PACKAGE_COLLECTION
from .github_handler import Release
from .main import get_all_packages
from pathlib import Path

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
    copy_extra_files: typing.List[typing.Tuple[str]]
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
            raise NotImplementedError
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
) -> typing.List[str]:
    if "depend" in pkg_info:
        deps = []
        for dep in pkg_info["depend"]:
            if dep.startswith("collection-"):
                deps.append(dep)
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
    checksums.append(checksums_regex_main.search(body).group("checksum"))
    checksums_regex_extra = re.compile(
        fr"(?P<checksum>[a-zA-Z0-9]*)  ({pkg}-extra-files\.tar\.xz)"
    )
    checksums.append(checksums_regex_extra.search(body).group("checksum"))
    return checksums


def main(repo_path: Path):
    jinja = JinjaHandler()
    version = get_version()
    for pkg in PACKAGE_COLLECTION:
        all_pkg = get_all_packages()
        backup = []
        copy_extra_files = []
        extra_cleanup_scripts_sed = []
        extra_cleanup_scripts_final = []
        if pkg == "texlive-core":
            package = Package(
                name=pkg,
                desc="TeX Live core distribution",
                deps=get_groups(PACKAGE_COLLECTION[pkg], all_pkg),
                groups=[],
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
                extra_cleanup_scripts_final.append("mflua")
            package = Package(
                name=pkg,
                desc=all_pkg[PACKAGE_COLLECTION[pkg]]["shortdesc"],
                deps=find_collection_dependencies(all_pkg[PACKAGE_COLLECTION[pkg]]),
                groups=get_groups(PACKAGE_COLLECTION[pkg], all_pkg),
                sha256sums=get_checksums(pkg),
                backup=backup,
                copy_extra_files=copy_extra_files,
                extra_cleanup_scripts_sed=extra_cleanup_scripts_sed,
                extra_cleanup_scripts_final=extra_cleanup_scripts_final,
            )
            template = jinja.get_template()
        template = template.render(package=package, version=version)
        pkgbuild_location = repo_path / f"mingw-w64-{pkg}" / "PKGBUILD"
        with pkgbuild_location.open("w", encoding="utf-8") as f:
            f.write(template)
