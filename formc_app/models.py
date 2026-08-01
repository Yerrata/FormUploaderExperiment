from __future__ import annotations

from datetime import date, datetime, time, timezone
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CaseStatus(StrEnum):
    GUEST_CAPTURE = "GUEST_CAPTURE"
    GUEST_REVIEW = "GUEST_REVIEW"
    NEEDS_ANSWERS = "NEEDS_ANSWERS"
    READY_FOR_FILING = "READY_FOR_FILING"
    FILING = "FILING"
    PRE_SUBMIT_EVIDENCE_SEALED = "PRE_SUBMIT_EVIDENCE_SEALED"
    VERIFIED = "VERIFIED"
    BLOCKED = "BLOCKED"
    SUBMITTED_UNVERIFIED = "SUBMITTED_UNVERIFIED"


FieldSource = Literal[
    "passport_dummy",
    "visa_dummy",
    "guest_answer",
    "guest_correction",
    "staff",
]


class CandidateField(BaseModel):
    value: str | None = None
    source: FieldSource
    original_value: str | None = None
    corrected_at: datetime | None = None

    @field_validator("value", "original_value")
    @classmethod
    def trim_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class CandidateFormC(BaseModel):
    case_id: str
    fields: dict[str, CandidateField]
    guest_confirmed_at: datetime | None = None
    validated_at: datetime | None = None

    def value(self, field_name: str) -> str | None:
        field = self.fields.get(field_name)
        return field.value if field else None

    def missing(self, required_fields: tuple[str, ...]) -> list[str]:
        return [name for name in required_fields if not self.value(name)]


class CaseMetadata(BaseModel):
    case_id: str
    guest_token: str
    guest_token_expires_at: datetime
    created_at: datetime = Field(default_factory=utc_now)
    check_in_date: date
    check_out_date: date | None = None
    arrival_time_hotel: time | None = None
    room: str
    form_b_reference: str | None = None
    dummy_profile: str
    passport_document: str | None = None
    visa_document: str | None = None
    guest_photo_document: str | None = None


class CaseState(BaseModel):
    case_id: str
    status: CaseStatus = CaseStatus.GUEST_CAPTURE
    status_changed_at: datetime = Field(default_factory=utc_now)
    status_message: str = "Waiting for document photographs"
    attempt: int = 0


class EvidenceManifest(BaseModel):
    case_id: str
    attempt: int
    captured_at: datetime
    candidate_sha256: str
    screenshot_sha256: str
    combined_sha256: str
    screenshot_path: str
    submitted_at: datetime | None = None
    acknowledgement: str | None = None
    acknowledgement_screenshot_path: str | None = None


class FilingRequest(BaseModel):
    case_id: str
    request_version: int = 1
    requested_at: datetime = Field(default_factory=utc_now)
    candidate_sha256: str
    guest_photo_sha256: str | None = None
    guest_photo_source: Literal["guest_camera"] | None = None
    guest_photo_suitability_confirmed_at: datetime | None = None

    @model_validator(mode="after")
    def require_version_two_photo_contract(self) -> "FilingRequest":
        if self.request_version >= 2 and (
            not self.guest_photo_sha256
            or self.guest_photo_source is None
            or self.guest_photo_suitability_confirmed_at is None
        ):
            raise ValueError("Version 2 Filing Requests must seal the approved guest photo")
        return self


class CaseSummary(BaseModel):
    metadata: CaseMetadata
    state: CaseState
    candidate: CandidateFormC | None = None
    evidence: EvidenceManifest | None = None


class MockSubmission(BaseModel):
    case_id: str
    acknowledgement: str
    submitted_at: datetime = Field(default_factory=utc_now)
    fields: dict[str, str]

    @model_validator(mode="after")
    def require_values(self) -> "MockSubmission":
        if any(not value.strip() for value in self.fields.values()):
            raise ValueError("Mock Form C fields must all be populated")
        return self
