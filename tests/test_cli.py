from __future__ import annotations

import logging
import re

from cisco_eox_query import cli
from cisco_eox_query.v5.models import EOXResponse


class _StubClient:
    def __init__(self, payload: dict):
        self.response = EOXResponse.model_validate(payload)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None

    def search_by_product_ids(self, *args, **kwargs):
        return self.response

    def search_by_serial_numbers(self, *args, **kwargs):
        return self.response

    def search_by_software_releases(self, *args, **kwargs):
        return self.response

    def search_by_dates(self, *args, **kwargs):
        return self.response


def test_parser_subcommands():
    parser = cli.build_parser()
    for argv in [
        ["pid", "WIC-1T="],
        ["serial", "FHK0933224R"],
        ["software", "12.4(15)T,IOS"],
        ["dates", "2011-01-01", "2015-12-31"],
    ]:
        assert parser.parse_args(argv).command == argv[0]


def test_main_pid_prints_records(monkeypatch, capsys, eox_response_payload):
    monkeypatch.setattr(cli, "EOXClient", lambda **kwargs: _StubClient(eox_response_payload))
    assert cli.main(["--access-token", "t", "pid", "WIC-1T="]) == 0
    out = capsys.readouterr().out
    assert "WIC-1T=" in out
    assert "2009-12-28" in out
    assert "HWIC-1T=" in out


def test_main_no_credentials(monkeypatch, caplog):
    monkeypatch.delenv("EOX_CLIENT_ID", raising=False)
    monkeypatch.delenv("EOX_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("EOX_ACCESS_TOKEN", raising=False)
    assert cli.main(["pid", "WIC-1T="]) == 1
    assert "credentials required" in caplog.text


def test_main_empty_results(monkeypatch, caplog):
    monkeypatch.setattr(cli, "EOXClient", lambda **kwargs: _StubClient({"EOXRecord": []}))
    assert cli.main(["--access-token", "t", "serial", "FHK0933224R"]) == 0
    assert "No EOX records found" in caplog.text


def test_main_error_payload_fails(monkeypatch, caplog):
    payload = {"EOXError": {"ErrorID": "SSA_ERR_034", "ErrorDescription": "Access denied."}}
    monkeypatch.setattr(cli, "EOXClient", lambda **kwargs: _StubClient(payload))
    assert cli.main(["--access-token", "t", "pid", "WIC-1T="]) == 1
    assert "Access denied" in caplog.text


def test_log_format_constants():
    assert cli.LOG_FORMAT == "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    assert cli.LOG_DATEFMT == "%Y-%m-%d %H:%M:%S"


def test_log_format_output():
    formatter = logging.Formatter(cli.LOG_FORMAT, cli.LOG_DATEFMT)
    record = logging.LogRecord(
        name="cisco_eox_query.cli",
        level=logging.ERROR,
        pathname="cli.py",
        lineno=1,
        msg="boom",
        args=(),
        exc_info=None,
    )
    line = formatter.format(record)
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} - ERROR - cisco_eox_query\.cli - boom", line)


def test_verbose_levels():
    assert cli._log_level(0) == logging.WARNING
    assert cli._log_level(1) == logging.INFO
    assert cli._log_level(2) == logging.DEBUG