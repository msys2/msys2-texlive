from pathlib import Path
import shutil
import os
from texlive.requests_handler import find_mirror, download_and_retry
import pytest

@pytest.fixture
def setup_texlive_tlpdb(tmp_path):
    cur_dir = os.getcwd()
    file = Path(__file__).parent.resolve().parent / "texlive.tlpdb"
    if not file.exists():
        url = find_mirror() + "tlpkg/texlive.tlpdb"
        download_and_retry(url,file)
    shutil.copy(file,tmp_path / "texlive.tlpdb")
    os.chdir(tmp_path)
    yield file
    os.chdir(cur_dir)
