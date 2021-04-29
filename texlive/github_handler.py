import os
import sys
from os import environ
from pathlib import Path
from typing import Any, AnyStr, Dict, List, Union
from .logger import logger
from github import Github
from github.GithubException import GithubException, RateLimitExceededException
from github.GitRelease import GitRelease
from github.GitReleaseAsset import GitReleaseAsset
from github.Repository import Repository

REPO = os.getenv("REPO", "msys2/msys2-texlive")

_PathLike = Union[os.PathLike, AnyStr]


def get_credentials(use_pat: bool = False) -> Dict[str, Any]:
    if not use_pat:
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
    else:
        if "ALT_TOKEN" in environ:
            return {"login_or_token": environ["ALT_TOKEN"]}
        else:
            raise Exception("'ALT_TOKEN' env vars not set")


def get_github(use_pat: bool = False) -> Github:
    kwargs = get_credentials(use_pat)
    kwargs['per_page'] = 100
    gh = Github(**kwargs)
    return gh


def get_repo(use_pat: bool = False) -> Repository:
    gh = get_github(use_pat)
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
        except (GithubException, RateLimitExceededException) as e:
            # try again with PAT
            logger.error(e)
            repo = get_repo(use_pat=True)
            release = repo.get_release(environ["tag_act"].split("/")[-1])
            upload()
        print(f"Uploaded {asset_name} as {asset_label}")
    else:
        print("[Warning] Not upload Release Asset.", file=sys.stderr)
