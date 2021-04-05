import os
import sys
from os import environ
from pathlib import Path
from typing import Any, AnyStr, Dict, Union

from github import Github
from github.GithubException import GithubException
from github.Repository import Repository

REPO = "msys2/msys2-texlive"

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


def upload_asset(path: _PathLike) -> None:
    if whether_to_upload():
        path = Path(path)
        asset_name = path.name
        asset_label = asset_name

        repo = get_repo()
        release = repo.get_release(environ["tag_act"].split("/")[-1])

        def upload() -> None:
            release.upload_asset(str(path), label=asset_label, name=asset_name)

        try:
            upload()
        except GithubException:
            # try again
            upload()
        print(f"Uploaded {asset_name} as {asset_label}")
    else:
        print("[Warning] Not upload Release Asset.", file=sys.stderr)
