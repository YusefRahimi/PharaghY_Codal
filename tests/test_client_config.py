import os

from pharaghy_codal.client import CodalClient


def test_client_timeout_override():
    c = CodalClient(timeout=12.5, min_interval=0.5, max_retries=1)
    assert c._timeout == 12.5
    assert c._min_interval == 0.5
    assert c._max_retries == 1


def test_client_cache_dir(tmp_path):
    c = CodalClient(cache_dir=str(tmp_path / "cache"))
    assert c._cache_dir
    assert (tmp_path / "cache").is_dir()
