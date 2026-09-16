from __future__ import annotations

import importlib
import importlib.metadata

import cisco_eox_query


def test_version_falls_back_when_package_metadata_missing(monkeypatch):
    def boom(name):
        raise importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(importlib.metadata, "version", boom)
    importlib.reload(cisco_eox_query)
    assert cisco_eox_query.__version__ == "1.2.0"
