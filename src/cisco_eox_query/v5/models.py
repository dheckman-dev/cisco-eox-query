"""Pydantic models for Cisco EOX API v5 response payloads."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _is_blank(value: Any) -> bool:
    return isinstance(value, str) and not value.strip()


class EOXAPIError(RuntimeError):
    """Raised when a response contains an ``EOXError`` payload."""

    def __init__(self, error: EOXErrorInfo | None = None, message: str | None = None) -> None:
        super().__init__(message or error.error_description if error else message)
        self.error = error


class MigrationDetails(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    pid_active_flag: str | None = Field(default=None, alias="PIDActiveFlag")
    migration_information: str | None = Field(default=None, alias="MigrationInformation")
    migration_option: str | None = Field(default=None, alias="MigrationOption")
    migration_product_id: str | None = Field(default=None, alias="MigrationProductId")
    migration_product_name: str | None = Field(default=None, alias="MigrationProductName")
    migration_strategy: str | None = Field(default=None, alias="MigrationStrategy")
    migration_product_info_url: str | None = Field(default=None, alias="MigrationProductInfoURL")

    @field_validator("*", mode="before")
    @classmethod
    def _blank_to_none(cls, value: Any) -> Any:
        return None if _is_blank(value) else value


class EOXRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    eol_product_id: str | None = Field(default=None, alias="EOLProductID")
    product_id_description: str | None = Field(default=None, alias="ProductIDDescription")
    product_bulletin_number: str | None = Field(default=None, alias="ProductBulletinNumber")
    link_to_product_bulletin_url: str | None = Field(default=None, alias="LinkToProductBulletinURL")
    eox_external_announcement_date: date | None = Field(
        default=None, alias="EOXExternalAnnouncementDate"
    )
    end_of_sale_date: date | None = Field(default=None, alias="EndOfSaleDate")
    end_of_sw_maintenance_releases: date | None = Field(
        default=None, alias="EndOfSWMaintenanceReleases"
    )
    end_of_security_vul_support_date: date | None = Field(
        default=None, alias="EndOfSecurityVulSupportDate"
    )
    end_of_routine_failure_analysis_date: date | None = Field(
        default=None, alias="EndOfRoutineFailureAnalysisDate"
    )
    end_of_service_contract_renewal: date | None = Field(
        default=None, alias="EndOfServiceContractRenewal"
    )
    last_date_of_support: date | None = Field(default=None, alias="LastDateOfSupport")
    end_of_svc_attach_date: date | None = Field(default=None, alias="EndOfSvcAttachDate")
    updated_time_stamp: date | None = Field(default=None, alias="UpdatedTimeStamp")
    migration_details: MigrationDetails | None = Field(default=None, alias="EOXMigrationDetails")
    eox_input_type: str | None = Field(default=None, alias="EOXInputType")
    eox_input_value: str | None = Field(default=None, alias="EOXInputValue")

    @field_validator("*", mode="before")
    @classmethod
    def _normalise(cls, value: Any) -> Any:
        if isinstance(value, dict) and set(value) <= {"value", "dateFormat"}:
            value = value.get("value")
        return None if _is_blank(value) else value


class PaginationResponseRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    page_index: int | None = Field(default=None, alias="PageIndex")
    last_index: int | None = Field(default=None, alias="LastIndex")
    total_records: int | None = Field(default=None, alias="TotalRecords")
    page_records: int | None = Field(default=None, alias="PageRecords")

    @field_validator("*", mode="before")
    @classmethod
    def _blank_to_none(cls, value: Any) -> Any:
        return None if _is_blank(value) else value


class EOXErrorInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    error_id: str | None = Field(default=None, alias="ErrorID")
    error_description: str | None = Field(default=None, alias="ErrorDescription")
    error_data_type: str | None = Field(default=None, alias="ErrorDataType")
    error_data_value: str | None = Field(default=None, alias="ErrorDataValue")

    @field_validator("*", mode="before")
    @classmethod
    def _blank_to_none(cls, value: Any) -> Any:
        return None if _is_blank(value) else value


class EOXResponse(BaseModel):
    """Parsed response for any EOX v5 search method."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    pagination: PaginationResponseRecord | None = Field(
        default=None, alias="PaginationResponseRecord"
    )
    records: list[EOXRecord] = Field(default_factory=list, alias="EOXRecord")
    error: EOXErrorInfo | None = Field(default=None, alias="EOXError")

    @field_validator("records", mode="before")
    @classmethod
    def _normalise_records(cls, value: Any) -> Any:
        if value is None:
            return []
        if isinstance(value, dict):
            return [value]
        return value

    def raise_for_error(self) -> None:
        if self.error is not None:
            raise EOXAPIError(self.error)
