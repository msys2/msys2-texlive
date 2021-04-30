from texlive.utils import *
import time

def test_get_file_archive_name(monkeypatch):
    def wrong_time(*args,**kwargs):
        return "invalid"
    monkeypatch.setattr(time, "strftime", wrong_time)
    assert get_file_archive_name('test') == f"test-invalid.tar.xz" 

def test_get_file_name_for_extra_files():
    a=get_file_name_for_extra_files('test')
    assert a == "test-extra-files.tar.xz"
