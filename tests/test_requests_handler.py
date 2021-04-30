import time
from contextlib import contextmanager
import pytest
import requests

from texlive.requests_handler import *


@pytest.mark.parametrize("error_type", [requests.HTTPError, requests.ConnectionError])
@pytest.mark.parametrize(
    "function,params",
    [(find_mirror, []), (download_and_retry, ["test", "test"]), (retry_get, ["test"])],
)
def test_handle_error(monkeypatch, error_type, function, params):
    def mock_get(*args, **kwargs):
        raise error_type("Foo Error")

    def mock_sleep(*args, **kwargs):
        pass

    monkeypatch.setattr(requests, "get", mock_get)
    monkeypatch.setattr(time, "sleep", mock_sleep)
    with pytest.raises(requests.HTTPError) as error:
        function(*params)
    assert error.type == requests.HTTPError


def test_texlive_info_fallback(monkeypatch):
    m = find_mirror(texlive_info=True)
    assert m.startswith("https://texlive.info")

    class MockResponse:
        @property
        def status_code(self):
            return 404

    def patch_get(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr(requests, "get", patch_get)
    m = find_mirror(texlive_info=True)
    timenow = time.localtime()
    assert (
        "https://texlive.info/tlnet-archive/%d/%02d/%02d/tlnet/"
        % (
            timenow.tm_year,
            timenow.tm_mon,
            timenow.tm_mday - 1,
        )
        == m
    )


def test_basic_mirror_redirect(monkeypatch):
    class MockResponse:
        @property
        def url(self):
            return "https://fakeurl/"

    def patch_get(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr(requests, "get", patch_get)
    assert find_mirror() == "https://fakeurl/systems/texlive/tlnet/"


def test_basic_download(monkeypatch, tmp_path):
    class MockResponse:
        def __init__(self, raises) -> None:
            self.raises = raises

        def raise_for_status(self):
            if self.raises:
                raise requests.HTTPError("Weird Error")

        def iter_content(self, *args, **kwargs):
            return [b"sample"]

    @contextmanager
    def patch_get_raises(*args, **kwargs):
        yield MockResponse(raises=True)

    monkeypatch.setattr(requests, "get", patch_get_raises)
    with pytest.raises(requests.HTTPError):
        download("test", "test")

    @contextmanager
    def patch_get(*args, **kwargs):
        yield MockResponse(raises=False)

    monkeypatch.setattr(requests, "get", patch_get)
    download("test", tmp_path / "test")
    with open(tmp_path / "test") as f:
        f.read() == "sample"


def test_sucessful_download_and_retry(monkeypatch, tmp_path):
    class MockResponse:
        def __init__(self) -> None:
            pass

        def raise_for_status(self):
            pass

        def iter_content(self, *args, **kwargs):
            return [b"sample"]

    @contextmanager
    def patch_get(*args, **kwargs):
        yield MockResponse()

    monkeypatch.setattr(requests, "get", patch_get)
    download_and_retry("test", tmp_path / "test")
    with open(tmp_path / "test") as f:
        f.read() == "sample"
