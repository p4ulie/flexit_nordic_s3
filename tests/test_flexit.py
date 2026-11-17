import importlib

import pytest


def test_import_without_env(monkeypatch):
    monkeypatch.delenv("FLEXIT_HOST", raising=False)
    monkeypatch.delenv("FLEXIT_DEVICE_ID", raising=False)
    importlib.import_module("flexit_nordic.flexit")


def test_config_reads_env(monkeypatch):
    from flexit_nordic.flexit import config

    monkeypatch.setenv("FLEXIT_HOST", "10.0.0.1")
    monkeypatch.setenv("FLEXIT_DEVICE_ID", "2")
    assert config() == ("10.0.0.1", 2)


def test_config_missing_exits(monkeypatch):
    from flexit_nordic.flexit import config

    monkeypatch.delenv("FLEXIT_HOST", raising=False)
    monkeypatch.delenv("FLEXIT_DEVICE_ID", raising=False)
    with pytest.raises(SystemExit):
        config()
