from __future__ import annotations

import logging
import re

import pytest

from cisco_eox_query import RateLimitError, cli
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


def test_main_record_without_migration_details_does_not_crash(monkeypatch, capsys):
    payload = {"EOXRecord": [{"EOLProductID": "WIC-1T=", "EndOfSaleDate": "2009-12-28"}]}
    monkeypatch.setattr(cli, "EOXClient", lambda **kwargs: _StubClient(payload))
    assert cli.main(["--access-token", "t", "pid", "WIC-1T="]) == 0
    assert "WIC-1T=" in capsys.readouterr().out


def test_main_serial_dispatch_prints_product_id(monkeypatch, capsys, eox_response_payload):
    monkeypatch.setattr(cli, "EOXClient", lambda **kwargs: _StubClient(eox_response_payload))
    assert cli.main(["--access-token", "t", "serial", "FHK0933224R"]) == 0
    assert "WIC-1T=" in capsys.readouterr().out


def test_main_software_dispatch(monkeypatch, eox_response_payload):
    monkeypatch.setattr(cli, "EOXClient", lambda **kwargs: _StubClient(eox_response_payload))
    assert cli.main(["--access-token", "t", "software", "12.4(15)T,IOS"]) == 0


def test_main_dates_attribs_dispatch(monkeypatch, eox_response_payload):
    monkeypatch.setattr(cli, "EOXClient", lambda **kwargs: _StubClient(eox_response_payload))
    assert (
        cli.main(
            [
                "--access-token",
                "t",
                "dates",
                "2011-01-01",
                "2015-12-31",
                "--attribs",
                "EO_SALES_DATE,EO_LAST_SUPPORT_DATE",
            ]
        )
        == 0
    )


def test_main_version_flag(capsys):
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--version"])
    assert exc_info.value.code == 0
    assert "eox-query" in capsys.readouterr().out


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


def test_main_rate_limit_exits_gracefully(monkeypatch, caplog):
    class _Limited:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return None

        def search_by_product_ids(self, *args, **kwargs):
            raise RateLimitError("exceeded the Cisco API rate limit after 3 retries")

    monkeypatch.setattr(cli, "EOXClient", lambda **kwargs: _Limited())
    assert cli.main(["--access-token", "t", "pid", "WIC-1T="]) == cli.EXIT_RATE_LIMIT
    assert "rate limit" in caplog.text.lower()


def test_main_with_client_credentials(monkeypatch, capsys, eox_response_payload):
    captured = {}

    def fake_client(**kwargs):
        captured.update(kwargs)
        return _StubClient(eox_response_payload)

    monkeypatch.setattr(cli, "EOXClient", fake_client)
    assert cli.main(["--client-id", "cid", "--client-secret", "sec", "pid", "WIC-1T="]) == 0
    assert captured["client_id"] == "cid"
    assert captured["client_secret"] == "sec"
    assert "WIC-1T=" in capsys.readouterr().out


def test_dispatch_unhandled_command_raises():
    import argparse

    args = argparse.Namespace(command="bogus")
    with pytest.raises(AssertionError):
        cli._dispatch(None, args)


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
    assert re.fullmatch(
        r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} - ERROR - cisco_eox_query\.cli - boom", line
    )


def test_verbose_levels():
    assert cli._log_level(0) == logging.WARNING
    assert cli._log_level(1) == logging.INFO
    assert cli._log_level(2) == logging.DEBUG


def test_collect_missing_last_index_returns_records():
    def request_fn(*args, **kwargs):
        return EOXResponse.model_validate(
            {
                "PaginationResponseRecord": {"PageIndex": 1, "TotalRecords": 1, "PageRecords": 1},
                "EOXRecord": [{"EOLProductID": "P1"}],
            }
        )

    records = cli._collect(request_fn)
    assert [r.eol_product_id for r in records] == ["P1"]


def test_collect_runaway_pagination_raises():
    from cisco_eox_query import PaginationError

    calls = []

    def request_fn(*args, **kwargs):
        page = kwargs["page"]
        calls.append(page)
        return EOXResponse.model_validate(
            {
                "PaginationResponseRecord": {"PageIndex": page, "LastIndex": page + 1},
                "EOXRecord": [{"EOLProductID": f"P{page}"}],
            }
        )

    with pytest.raises(PaginationError):
        cli._collect(request_fn)
    assert len(calls) == cli.DEFAULT_MAX_PAGES


def test_main_examples_flag(capsys):
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--examples"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "Examples" in out
    assert "pid" in out
    assert "serial" in out


def test_main_pid_examples_flag(capsys):
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["pid", "--examples"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "Examples for 'pid'" in out
    assert "WS-C2960X-48TS-L" in out


def test_main_serial_examples_flag(capsys):
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["serial", "--examples"])
    assert exc_info.value.code == 0
    assert "JAE11108ESH" in capsys.readouterr().out


def test_main_software_examples_flag(capsys):
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["software", "--examples"])
    assert exc_info.value.code == 0
    assert "12.4(15)T,IOS" in capsys.readouterr().out


def test_main_dates_examples_flag(capsys):
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["dates", "--examples"])
    assert exc_info.value.code == 0
    assert "2011-01-01" in capsys.readouterr().out


def test_help_contains_examples(capsys):
    with pytest.raises(SystemExit) as exc_info:
        cli.build_parser().parse_args(["--help"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "examples:" in out
    assert "eox-query --client-id" in out


def test_subcommand_help_contains_examples(capsys):
    with pytest.raises(SystemExit) as exc_info:
        cli.build_parser().parse_args(["pid", "--help"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "examples:" in out
    assert "WS-C2960X-48TS-L" in out


def test_format_examples():
    text = cli.format_examples([("Query a product", "eox-query pid WIC-1T=")], title="Examples")
    assert text.startswith("Examples\n")
    assert "Query a product:" in text
    assert "  eox-query pid WIC-1T=" in text


def test_format_epilog():
    text = cli.format_epilog([("Query a product", "eox-query pid WIC-1T=")])
    assert text == "examples:\n  eox-query pid WIC-1T="
