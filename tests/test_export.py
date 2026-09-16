from __future__ import annotations

import csv
import io

import cisco_eox_query
from cisco_eox_query import export_to_csv
from cisco_eox_query.export import CSV_COLUMNS
from cisco_eox_query.v5.models import EOXRecord


def _rows(csv_text: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(csv_text)))


def _column_index(name: str) -> int:
    return CSV_COLUMNS.index(name)


def test_header_row_matches_csv_columns(eox_record_payload):
    record = EOXRecord.model_validate(eox_record_payload)
    text = export_to_csv([record])
    assert text.splitlines()[0] == ",".join(CSV_COLUMNS)


def test_csv_header_uses_query_type():
    record = EOXRecord.model_validate({"EOLProductID": "WIC-1T="})
    header = _rows(export_to_csv([record]))[0]
    assert "QueryType" in header
    assert "EOXInputType" not in header


def test_csv_query_type_column_contains_normalized_value(eox_record_payload):
    record = EOXRecord.model_validate(eox_record_payload)
    row = _rows(export_to_csv([record]))[1]
    assert row[_column_index("QueryType")] == "queried_product_id"


def test_full_record_row(eox_record_payload):
    record = EOXRecord.model_validate(eox_record_payload)
    row = _rows(export_to_csv([record]))[1]
    assert row[_column_index("EOLProductID")] == "WIC-1T="
    assert row[_column_index("EndOfSaleDate")] == "2009-12-28"
    assert row[_column_index("MigrationProductId")] == "HWIC-1T="
    assert row[_column_index("MigrationProductInfoURL")] == "https://www.cisco.com"
    assert row[_column_index("QueryType")] == "queried_product_id"


def test_none_values_serialize_as_empty_cells():
    record = EOXRecord.model_validate({"EOLProductID": "WIC-1T="})
    row = _rows(export_to_csv([record]))[1]
    assert row[0] == "WIC-1T="
    assert row[1:] == [""] * (len(CSV_COLUMNS) - 1)


def test_no_migration_details_leaves_migration_cells_empty():
    record = EOXRecord.model_validate({"EOLProductID": "WIC-1T=", "EndOfSaleDate": "2009-12-28"})
    row = _rows(export_to_csv([record]))[1]
    migration_columns = [c for c in CSV_COLUMNS if c.startswith("Migration")]
    for column in migration_columns:
        assert row[_column_index(column)] == ""


def test_special_characters_round_trip():
    record = EOXRecord.model_validate(
        {
            "EOLProductID": "WIC-1T=",
            "ProductIDDescription": 'comma, "double quote" and\nnewline',
        }
    )
    row = _rows(export_to_csv([record]))[1]
    assert row[_column_index("ProductIDDescription")] == 'comma, "double quote" and\nnewline'


def test_formula_trigger_values_serialized_verbatim():
    record = EOXRecord.model_validate(
        {
            "EOLProductID": "WIC-1T=",
            "ProductIDDescription": "=1+2",
            "EOXInputValue": '=HYPERLINK("http://evil.example")',
        }
    )
    row = _rows(export_to_csv([record]))[1]
    assert row[_column_index("ProductIDDescription")] == "=1+2"
    assert row[_column_index("EOXInputValue")] == '=HYPERLINK("http://evil.example")'


def test_non_ascii_values_round_trip():
    record = EOXRecord.model_validate(
        {
            "EOLProductID": "WIC-1T=",
            "ProductIDDescription": "Café — WAN Interface Card",
        }
    )
    row = _rows(export_to_csv([record]))[1]
    assert row[_column_index("ProductIDDescription")] == "Café — WAN Interface Card"


def test_output_path_absolute_writes_matching_string(eox_record_payload, tmp_path):
    record = EOXRecord.model_validate(eox_record_payload)
    expected = export_to_csv([record])
    target = tmp_path / "out.csv"
    result = export_to_csv([record], output=target)
    assert result is None
    assert target.is_absolute()
    assert target.read_text(encoding="utf-8") == expected


def test_empty_records_only_header():
    text = export_to_csv([])
    assert text == ",".join(CSV_COLUMNS) + "\n"


def test_output_none_returns_str(eox_record_payload):
    record = EOXRecord.model_validate(eox_record_payload)
    assert isinstance(export_to_csv([record]), str)


def test_output_path_writes_utf8_file(eox_record_payload, tmp_path):
    record = EOXRecord.model_validate(eox_record_payload)
    expected = export_to_csv([record])
    target = tmp_path / "out.csv"
    result = export_to_csv([record], output=target)
    assert result is None
    assert target.read_text(encoding="utf-8") == expected


def test_output_filelike_writes_and_does_not_close(eox_record_payload):
    record = EOXRecord.model_validate(eox_record_payload)
    stream = io.StringIO()
    result = export_to_csv([record], output=stream)
    assert result is None
    assert not stream.closed
    assert stream.getvalue() == export_to_csv([record])


def test_export_to_csv_in_package_root():
    assert cisco_eox_query.export_to_csv is export_to_csv
    assert "export_to_csv" in cisco_eox_query.__all__
