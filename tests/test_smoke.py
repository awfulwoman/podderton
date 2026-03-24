import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_import_config():
    import config
    assert config is not None


def test_import_files():
    import files
    assert files is not None


def test_import_subscribe():
    import subscribe
    assert subscribe is not None


def test_import_utils():
    import utils
    assert utils is not None


def test_import_remote():
    import remote
    assert remote is not None


def test_import_server():
    import server
    assert server is not None


def test_import_publish():
    import publish
    assert publish is not None
