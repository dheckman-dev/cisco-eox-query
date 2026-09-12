from __future__ import annotations

import pytest


@pytest.fixture
def eox_record_payload() -> dict:
    return {
        "EOLProductID": "WIC-1T=",
        "ProductIDDescription": "WAN Interface Card",
        "ProductBulletinNumber": "EOL6640",
        "LinkToProductBulletinURL": "https://www.cisco.com",
        "EOXExternalAnnouncementDate": {"value": "2008-12-28", "dateFormat": "YYYY-MM-DD"},
        "EndOfSaleDate": {"value": "2009-12-28", "dateFormat": "YYYY-MM-DD"},
        "EndOfSWMaintenanceReleases": {"value": " ", "dateFormat": "YYYY-MM-DD"},
        "EndOfSecurityVulSupportDate": {"value": "2012-12-15", "dateFormat": "YYYY-MM-DD"},
        "EndOfRoutineFailureAnalysisDate": {"value": " ", "dateFormat": "YYYY-MM-DD"},
        "EndOfServiceContractRenewal": {"value": "2014-03-28", "dateFormat": "YYYY-MM-DD"},
        "LastDateOfSupport": {"value": "2014-12-27", "dateFormat": "YYYY-MM-DD"},
        "EndOfSvcAttachDate": {"value": "2012-10-31", "dateFormat": "YYYY-MM-DD"},
        "UpdatedTimeStamp": {"value": "2009-08-25", "dateFormat": "YYYY-MM-DD"},
        "EOXMigrationDetails": {
            "PIDActiveFlag": "Y",
            "MigrationInformation": "WAN Interface Card",
            "MigrationOption": "Enter PID(s)",
            "MigrationProductId": "HWIC-1T=",
            "MigrationProductName": " ",
            "MigrationStrategy": " ",
            "MigrationProductInfoURL": "https://www.cisco.com",
        },
        "EOXInputType": "ShowEOXByPids",
        "EOXInputValue": "WIC-1T= ",
    }


@pytest.fixture
def eox_response_payload(eox_record_payload) -> dict:
    return {
        "PaginationResponseRecord": {
            "PageIndex": 1,
            "LastIndex": 1,
            "TotalRecords": 1,
            "PageRecords": 1,
        },
        "EOXRecord": [eox_record_payload],
    }