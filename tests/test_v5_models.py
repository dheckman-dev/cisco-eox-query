from __future__ import annotations

from datetime import date

import pytest

from cisco_eox_query.v5.models import EOXAPIError, EOXResponse


def test_parse_full_response(eox_response_payload):
    response = EOXResponse.model_validate(eox_response_payload)
    assert response.error is None
    assert response.pagination.page_index == 1
    assert response.pagination.last_index == 1
    assert response.pagination.total_records == 1

    record = response.records[0]
    assert record.eol_product_id == "WIC-1T="
    assert record.end_of_sale_date == date(2009, 12, 28)
    assert record.last_date_of_support == date(2014, 12, 27)
    assert record.eox_external_announcement_date == date(2008, 12, 28)
    assert record.end_of_sw_maintenance_releases is None
    assert record.migration_details is not None
    assert record.migration_details.migration_product_id == "HWIC-1T="
    assert record.migration_details.migration_strategy is None


def test_blank_dates_become_none(eox_record_payload):
    eox_record_payload["EndOfSaleDate"] = {"value": " ", "dateFormat": "YYYY-MM-DD"}
    record = EOXResponse.model_validate({"EOXRecord": [eox_record_payload]}).records[0]
    assert record.end_of_sale_date is None


def test_error_payload_raise_for_error(eox_response_payload):
    eox_response_payload["EOXRecord"] = []
    eox_response_payload["EOXError"] = {
        "ErrorID": "SSA_ERR_026",
        "ErrorDescription": "EOX information does not exist for the following product ID(s): ILPM-8=",
        "ErrorDataType": "PRODUCT_ID",
        "ErrorDataValue": "ILPM-8=",
    }
    response = EOXResponse.model_validate(eox_response_payload)
    assert response.records == []
    assert response.error.error_id == "SSA_ERR_026"
    with pytest.raises(EOXAPIError) as exc_info:
        response.raise_for_error()
    assert exc_info.value.error.error_data_value == "ILPM-8="


def test_unknown_fields_ignored(eox_record_payload):
    eox_record_payload["SomeFutureField"] = "ignored"
    record = EOXResponse.model_validate({"EOXRecord": [eox_record_payload]}).records[0]
    assert record.eol_product_id == "WIC-1T="


def test_empty_payload():
    response = EOXResponse.model_validate({})
    assert response.records == []
    assert response.pagination is None
    assert response.error is None


def test_null_eoxrecord_means_empty_records():
    response = EOXResponse.model_validate({"EOXRecord": None})
    assert response.records == []


def test_single_record_dict_is_accepted():
    response = EOXResponse.model_validate({"EOXRecord": {"EOLProductID": "WIC-1T="}})
    assert len(response.records) == 1
    assert response.records[0].eol_product_id == "WIC-1T="


def test_string_pagination_fields_coerced_to_int():
    response = EOXResponse.model_validate(
        {
            "PaginationResponseRecord": {
                "PageIndex": "1",
                "LastIndex": "2",
                "TotalRecords": "2",
                "PageRecords": "1",
            }
        }
    )
    assert response.pagination.page_index == 1
    assert response.pagination.last_index == 2
    assert response.pagination.total_records == 2
    assert response.pagination.page_records == 1