import sys
from pathlib import Path
from textwrap import dedent

sys.path.append(str(Path(__file__).parent.resolve().parent))

from texlive.github_handler import *
from texlive.utils import find_checksum_from_url

template = dedent(
    """\
    # MSYS2 TexLive {version}
    See https://github.com/msys2/msys2-texlive for more information.
    
    ## Checksums
    ```
    {checksums_string}
    ```
    """
)

repo = get_repo()
release = repo.get_release(environ["tag_act"].split("/")[-1])
release_assets = get_release_assets(release)

checksums = {}

for asset in release_assets:
    url = asset.browser_download_url
    checksums[asset.name] = find_checksum_from_url(url, "sha256")

checksums_string = "\n".join(
    [f"{checksum}  {name}" for name, checksum in checksums.items()]
)

release.update_release(
    name=f"MSYS2 TexLive {release.tag_name}",
    message=template.format(
        version=release.tag_name, checksums_string=checksums_string
    ),
)
