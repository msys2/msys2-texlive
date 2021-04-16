import os
import re
import sys
from os import environ
from pathlib import Path
from textwrap import dedent
from typing import Any, AnyStr, Dict, List, Union

from github import Github
from github.GithubException import GithubException
from github.GitRelease import GitRelease
from github.GitReleaseAsset import GitReleaseAsset
from github.Repository import Repository

from .utils import find_checksum_from_file

REPO = os.getenv("REPO", "msys2/msys2-texlive")

_PathLike = Union[os.PathLike, AnyStr]


def get_credentials() -> Dict[str, Any]:
    if "GITHUB_TOKEN" in environ:
        return {"login_or_token": environ["GITHUB_TOKEN"]}
    elif "GITHUB_USER" in environ and "GITHUB_PASS" in environ:
        return {
            "login_or_token": environ["GITHUB_USER"],
            "password": environ["GITHUB_PASS"],
        }
    else:
        raise Exception(
            "'GITHUB_TOKEN' or 'GITHUB_USER'/'GITHUB_PASS' env vars not set"
        )


def get_github() -> Github:
    kwargs = get_credentials()
    gh = Github(**kwargs)
    return gh


def get_repo() -> Repository:
    gh = get_github()
    return gh.get_repo(REPO, lazy=True)


def whether_to_upload() -> bool:
    if environ["event"] == "release":
        return True
    return False


def get_release_assets(release: GitRelease) -> List[GitReleaseAsset]:
    assets = []
    for asset in release.get_assets():
        assets.append(asset)
    return assets


def update_readme(asset_name: str, path: Path, release: GitRelease):
    checksum = find_checksum_from_file(path, "sha256")
    release_body = release.body
    if release.body == "":
        content = dedent(
            f"""
            MSYS2 TexLive Release v{release.title}
            <!--checksum-start-->
            ```
            {checksum} {asset_name}
            ```
            <!--checksum-end-->
            """
        )
    else:
        pattern = re.compile(
            r"<!--checksum-start-->\n```(?P<checksum>[^`]*)```\n<!--checksum-end-->",
            re.MULTILINE,
        )

        def add_checksum(matchobj: re.Match):
            return dedent(
                f"""\
            <!--checksum-start-->
            ```
            {matchobj.group('checksum')}
            {checksum} {asset_name}
            ```
            <!--checksum-end-->
            """
            )

        content = pattern.sub(add_checksum, release_body)
    release.update_release(
        name=release.tag_name,
        message=content,
    )


def upload_asset(path: _PathLike) -> None:
    if whether_to_upload():
        path = Path(path)
        asset_name = path.name
        asset_label = asset_name

        repo = get_repo()
        release = repo.get_release(environ["tag_act"].split("/")[-1])

        def upload() -> None:
            release.upload_asset(str(path), label=asset_label, name=asset_name)

        for asset in get_release_assets(release):
            if asset_name == asset.name:
                asset.delete_asset()
                break
        try:
            upload()
        except GithubException:
            # try again
            upload()
        print(f"Uploaded {asset_name} as {asset_label}")
        update_readme(asset_name, path, release)
    else:
        print("[Warning] Not upload Release Asset.", file=sys.stderr)
