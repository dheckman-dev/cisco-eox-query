"""Constants specific to the Cisco EOX API v5."""

from __future__ import annotations

from typing import Literal

MAX_INPUTS = 20

ResponseEncoding = Literal["json", "xml"]
SoftwareRelease = tuple[str, str] | str

EOX_INPUT_TYPE_ALIASES: dict[str, str] = {
    "showeoxbypids": "queried_product_id",
    "showeoxbyproductid": "queried_product_id",
    "showeoxbyserialnumber": "queried_serial",
    "showeoxbydates": "queried_dates",
    "showeoxbysoftware": "queried_software",
    "showeoxbyswreleasestring": "queried_software",
}

QUERY_TYPES: frozenset[str] = frozenset(EOX_INPUT_TYPE_ALIASES.values())

EOX_ATTRIBS = frozenset(
    {
        "EO_EXT_ANNOUNCE_DATE",
        "EO_SALES_DATE",
        "EO_FAIL_ANALYSIS_DATE",
        "EO_SVC_ATTACH_DATE",
        "EO_SW_MAINTENANCE_DATE",
        "EO_SECURITY_VUL_SUPPORT_DATE",
        "EO_CONTRACT_RENEW_DATE",
        "EO_LAST_SUPPORT_DATE",
        "UPDATE_TIMESTAMP",
        "UPDATED_TIMESTAMP",
    }
)

OS_TYPES = frozenset(
    {
        "ACNS",
        "ACSW",
        "ALTIGAOS",
        "ASA",
        "ASYNCOS",
        "CATOS",
        "CDS-IS",
        "CDS-TV",
        "CDS-VN",
        "CDS-VQE",
        "CTS",
        "ECDS",
        "FWSM-OS",
        "GSS",
        "IOS",
        "IOS XR",
        "IOS-XE",
        "IPS",
        "NAM",
        "NX-OS",
        "ONS",
        "PIXOS",
        "SAN-OS",
        "STAR OS",
        "TC",
        "TE",
        "UCS NX-OS",
        "VCS",
        "VDS-IS",
        "WAAS",
        "WANSW BPX/IGX/IPX",
        "WEBNS",
        "WLC",
        "WLSE-OS",
        "XC",
    }
)

__all__ = [
    "EOX_ATTRIBS",
    "EOX_INPUT_TYPE_ALIASES",
    "MAX_INPUTS",
    "OS_TYPES",
    "QUERY_TYPES",
    "ResponseEncoding",
    "SoftwareRelease",
]
