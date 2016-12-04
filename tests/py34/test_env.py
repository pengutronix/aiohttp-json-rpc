import sys


def test_version():
    assert sys.version_info >= (3, 4)
