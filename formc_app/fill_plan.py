from __future__ import annotations

import argparse
import json
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from formc_app.domain import intended_stay_days
from formc_app.models import CandidateFormC
from formc_app.portal_mapping import (
    EMPLOYMENT_CHOICE_CODES,
    LIVE_SUBMISSION_CONTROL_IDS,
    PROPERTY_CONFIG_PORTAL_CONTROLS,
    PURPOSE_OF_VISIT_CHOICE_CODES,
    SEX_CHOICE_CODES,
    NEXT_DESTINATION_SCOPE_CODES,
)
from formc_app.property_config import (
    PropertyConfigError,
    YerattaPropertyConfig,
    load_property_config,
)
from formc_app.storage import CaseStore


class FillPlanStatus(StrEnum):
    READY = "READY"
    BLOCKED = "BLOCKED"


class FillAction(StrEnum):
    FILL_TEXT = "FILL_TEXT"
    SELECT_OPTION = "SELECT_OPTION"
    CHECK_RADIO = "CHECK_RADIO"
    UPLOAD_FILE = "UPLOAD_FILE"


class FillValueSource(StrEnum):
    CANDIDATE = "CANDIDATE"
    PROPERTY_CONFIGURATION = "PROPERTY_CONFIGURATION"
    CONSTANT = "CONSTANT"
    FILING_REQUEST = "FILING_REQUEST"


class FillOptionMatch(StrEnum):
    VALUE = "VALUE"
    LABEL = "LABEL"


class FillOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sequence: int
    source_field: str
    portal_control: str
    action: FillAction
    value: str
    value_source: FillValueSource
    value_sha256: str | None = None
    runtime_option_check_required: bool = False
    option_match: FillOptionMatch = FillOptionMatch.VALUE


class FillBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    field: str | None = None
    message: str


class PortalFillPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[3] = 3
    case_id: str
    candidate_sha256: str
    guest_photo_sha256: str | None = None
    catalogue_sha256: str | None = None
    property_config_sha256: str | None = None
    status: FillPlanStatus
    live_fill_enabled: bool = False
    live_submit_enabled: Literal[False] = False
    operations: list[FillOperation] = Field(default_factory=list)
    blockers: list[FillBlocker] = Field(default_factory=list)

    @model_validator(mode="after")
    def enforce_fill_only_gate(self) -> "PortalFillPlan":
        if self.live_fill_enabled != (
            self.status == FillPlanStatus.READY and not self.blockers
        ):
            raise ValueError("Live fill is enabled only for an unblocked READY plan")
        return self


DIRECT_FIELDS = {
    "surname": "applicant_surname",
    "given_name": "applicant_givenname",
    "permanent_address": "applicant_permaddr",
    "permanent_city": "applicant_permcity",
    "passport_number": "applicant_passpno",
    "passport_place_of_issue": "applicant_passplcofissue",
    "visa_number": "applicant_visano",
    "visa_place_of_issue": "applicant_visaplcoissue",
    "arrived_from_city": "applicant_arrivedfromcity",
    "arrived_from_place": "applicant_arrivedfromplace",
}

DATE_FIELDS = {
    "passport_date_of_issue": "applicant_passpdoissue",
    "passport_valid_until": "applicant_passpvalidtill",
    "visa_date_of_issue": "applicant_visadoissue",
    "visa_valid_until": "applicant_visavalidtill",
    "arrival_date_india": "applicant_doarrivalindia",
    "check_in_date": "applicant_doarrivalhotel",
}

OPTION_LABEL_FIELDS = {
    "nationality": "applicant_nationality",
    "permanent_country": "applicant_permcountry",
    "passport_issue_country": "passport_issue_country",
    "visa_issue_country": "visa_issue_country",
    "visa_type": "applicant_visatype",
    "arrived_from_country": "applicant_arrivedfromcountry",
}

DERIVED_FIELDS = {
    "check_out_date": "applicant_intnddurhotel",
}

def _canonical_bytes(value: BaseModel) -> bytes:
    return (
        json.dumps(value.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


class _PlanBuilder:
    def __init__(self):
        self.operations: list[FillOperation] = []
        self.blockers: list[FillBlocker] = []

    def block(self, code: str, message: str, *, field: str | None = None) -> None:
        self.blockers.append(FillBlocker(code=code, field=field, message=message))

    def _append(
        self,
        *,
        field: str,
        control: str,
        action: FillAction,
        value: str,
        source: FillValueSource = FillValueSource.CANDIDATE,
        source_field: str | None = None,
        value_sha256: str | None = None,
        runtime_option_check_required: bool = False,
        option_match: FillOptionMatch = FillOptionMatch.VALUE,
    ) -> None:
        if control in LIVE_SUBMISSION_CONTROL_IDS:
            self.block(
                "submission_control_forbidden",
                f"Fill plans may never target live submission control {control}.",
                field=field,
            )
            return
        self.operations.append(
            FillOperation(
                sequence=len(self.operations) + 1,
                source_field=source_field
                or f"{source.value.casefold()}.{field}",
                portal_control=control,
                action=action,
                value=value,
                value_source=source,
                value_sha256=value_sha256,
                runtime_option_check_required=runtime_option_check_required,
                option_match=option_match,
            )
        )

    def fill_text(
        self,
        *,
        field: str,
        control: str,
        value: str,
        source: FillValueSource = FillValueSource.CANDIDATE,
        source_field: str | None = None,
    ) -> None:
        self._append(
            field=field,
            control=control,
            action=FillAction.FILL_TEXT,
            value=value,
            source=source,
            source_field=source_field,
        )

    def select_value(
        self,
        *,
        field: str,
        control: str,
        value: str,
        source: FillValueSource = FillValueSource.CANDIDATE,
        source_field: str | None = None,
    ) -> None:
        self._append(
            field=field,
            control=control,
            action=FillAction.SELECT_OPTION,
            value=value,
            source=source,
            source_field=source_field,
        )

    def select_dynamic_value(
        self,
        *,
        field: str,
        control: str,
        value: str,
        source_field: str,
    ) -> None:
        self._append(
            field=field,
            control=control,
            action=FillAction.SELECT_OPTION,
            value=value,
            source=FillValueSource.PROPERTY_CONFIGURATION,
            source_field=source_field,
            runtime_option_check_required=True,
        )

    def select_dynamic_label(
        self,
        *,
        field: str,
        control: str,
        label: str,
        source_field: str,
    ) -> None:
        self._append(
            field=field,
            control=control,
            action=FillAction.SELECT_OPTION,
            value=label,
            source_field=source_field,
            runtime_option_check_required=True,
            option_match=FillOptionMatch.LABEL,
        )

    def select_label(self, *, field: str, control: str, label: str) -> None:
        self._append(
            field=field,
            control=control,
            action=FillAction.SELECT_OPTION,
            value=label,
            runtime_option_check_required=True,
            option_match=FillOptionMatch.LABEL,
        )

    def check_radio(self, *, field: str, control: str, value: str) -> None:
        self._append(
            field=field,
            control=control,
            action=FillAction.CHECK_RADIO,
            value=value,
        )

    def upload_file(
        self,
        *,
        field: str,
        control: str,
        relative_path: str,
        sha256: str,
    ) -> None:
        path = Path(relative_path)
        if (
            path.is_absolute()
            or ".." in path.parts
            or not relative_path.startswith("documents/")
        ):
            self.block(
                "guest_photo_path_invalid",
                "The guest photograph path is not a safe case-relative document path.",
                field=field,
            )
            return
        self._append(
            field=field,
            control=control,
            action=FillAction.UPLOAD_FILE,
            value=relative_path,
            source=FillValueSource.FILING_REQUEST,
            source_field="filing_request.guest_photo",
            value_sha256=sha256,
        )


def _candidate_value(
    candidate: CandidateFormC,
    field: str,
    builder: _PlanBuilder,
) -> str | None:
    return candidate.value(field)


def _portal_date(
    candidate: CandidateFormC,
    field: str,
    builder: _PlanBuilder,
) -> str | None:
    value = _candidate_value(candidate, field, builder)
    if value is None:
        return None
    try:
        return date.fromisoformat(value).strftime("%d/%m/%Y")
    except ValueError:
        return value


def _portal_time(
    candidate: CandidateFormC,
    field: str,
    builder: _PlanBuilder,
) -> str | None:
    value = _candidate_value(candidate, field, builder)
    if value is None:
        return None
    return value


def compile_fill_plan(
    *,
    candidate: CandidateFormC,
    property_config: YerattaPropertyConfig | None = None,
    candidate_sha256: str,
    guest_photo_path: str | None = None,
    guest_photo_sha256: str | None = None,
) -> PortalFillPlan:
    """Build a self-contained best-effort plan without validating portal data."""
    builder = _PlanBuilder()

    for field, control in DIRECT_FIELDS.items():
        value = _candidate_value(candidate, field, builder)
        if value is not None:
            builder.fill_text(field=field, control=control, value=value)

    for field, control in DATE_FIELDS.items():
        value = _portal_date(candidate, field, builder)
        if value is not None:
            builder.fill_text(field=field, control=control, value=value)

    arrival_time = _portal_time(candidate, "arrival_time_hotel", builder)
    if arrival_time is not None:
        builder.fill_text(
            field="arrival_time_hotel",
            control="applicant_timeoarrivalhotel",
            value=arrival_time,
        )

    check_in_value = _candidate_value(candidate, "check_in_date", builder)
    check_out_value = _candidate_value(candidate, "check_out_date", builder)
    if check_in_value is not None and check_out_value is not None:
        try:
            duration = intended_stay_days(check_in_value, check_out_value)
        except ValueError:
            pass
        else:
            builder.fill_text(
                field="check_out_date",
                control=DERIVED_FIELDS["check_out_date"],
                value=str(duration),
                source_field="candidate.check_in_date+candidate.check_out_date",
            )

    date_of_birth = _portal_date(candidate, "date_of_birth", builder)
    if date_of_birth is not None:
        builder.select_value(
            field="date_of_birth",
            control="dobformat",
            value="DY",
            source=FillValueSource.CONSTANT,
        )
        builder.fill_text(
            field="date_of_birth",
            control="applicant_dob",
            value=date_of_birth,
        )

    for field, control in OPTION_LABEL_FIELDS.items():
        value = _candidate_value(candidate, field, builder)
        if value is not None:
            builder.select_label(field=field, control=control, label=value)

    coded_choices = (
        ("sex", "applicant_sex", SEX_CHOICE_CODES, FillAction.SELECT_OPTION),
        ("employed_in_india", "employed", EMPLOYMENT_CHOICE_CODES, FillAction.CHECK_RADIO),
        (
            "purpose_of_visit",
            "applicant_purpovisit",
            PURPOSE_OF_VISIT_CHOICE_CODES,
            FillAction.SELECT_OPTION,
        ),
    )
    for field, control, choices, action in coded_choices:
        value = _candidate_value(candidate, field, builder)
        if value is None:
            continue
        portal_value = choices.get(value)
        portal_value = portal_value or value
        if action == FillAction.CHECK_RADIO:
            builder.check_radio(field=field, control=control, value=portal_value)
        else:
            builder.select_value(field=field, control=control, value=portal_value)

    destination_scope = _candidate_value(candidate, "next_destination_scope", builder)
    if destination_scope is not None:
        portal_scope = NEXT_DESTINATION_SCOPE_CODES.get(destination_scope)
        builder.check_radio(
            field="next_destination_scope",
            control="applicant_next_dest_country_flag_r",
            value=portal_scope or destination_scope,
        )

    destination_place = _candidate_value(candidate, "next_destination", builder)
    if destination_scope == "india":
        destination_state = _candidate_value(
            candidate, "next_destination_state", builder
        )
        destination_city = _candidate_value(
            candidate, "next_destination_city", builder
        )
        if destination_state is not None:
            builder.select_label(
                field="next_destination_state",
                control="applicant_next_destination_state_IN",
                label=destination_state,
            )
        if destination_city is not None:
            builder.select_dynamic_label(
                field="next_destination_city",
                control="applicant_next_destination_city_district_IN",
                label=destination_city,
                source_field="candidate.next_destination_city",
            )
        if destination_place is not None:
            builder.fill_text(
                field="next_destination",
                control="applicant_next_destination_place_IN",
                value=destination_place,
            )

    if property_config is not None:
        builder.fill_text(
            field="reference_address",
            control=PROPERTY_CONFIG_PORTAL_CONTROLS["reference_address"],
            value=property_config.reference_address,
            source=FillValueSource.PROPERTY_CONFIGURATION,
            source_field="property.reference_address",
        )
        builder.select_value(
            field="reference_state_code",
            control=PROPERTY_CONFIG_PORTAL_CONTROLS["reference_state_code"],
            value=property_config.reference_state_code,
            source=FillValueSource.PROPERTY_CONFIGURATION,
            source_field="property.reference_state_code",
        )
        builder.select_dynamic_value(
            field="reference_district_code",
            control=PROPERTY_CONFIG_PORTAL_CONTROLS["reference_district_code"],
            value=property_config.reference_district_code,
            source_field="property.reference_district_code",
        )
        builder.fill_text(
            field="reference_pin_code",
            control=PROPERTY_CONFIG_PORTAL_CONTROLS["reference_pin_code"],
            value=property_config.reference_pin_code,
            source=FillValueSource.PROPERTY_CONFIGURATION,
            source_field="property.reference_pin_code",
        )

    if guest_photo_path is not None and guest_photo_sha256 is not None:
        builder.upload_file(
            field="guest_photo",
            control="file1",
            relative_path=guest_photo_path,
            sha256=guest_photo_sha256,
        )
    plan = PortalFillPlan(
        case_id=candidate.case_id,
        candidate_sha256=candidate_sha256,
        guest_photo_sha256=guest_photo_sha256,
        catalogue_sha256=None,
        property_config_sha256=None,
        status=FillPlanStatus.READY,
        live_fill_enabled=True,
        operations=builder.operations,
        blockers=builder.blockers,
    )
    return plan


def prepare_fill_plan(*, store: CaseStore, data_root: Path, case_id: str) -> PortalFillPlan:
    """Persist a self-contained best-effort plan for the browser executor."""
    summary = store.get_summary(case_id)
    store.clear_fill_plan(case_id)
    candidate = summary.candidate
    if candidate is None:
        raise ValueError("Candidate Form C is missing")
    if candidate.case_id != case_id:
        raise ValueError("Candidate case ID does not match its case folder")

    try:
        property_config = load_property_config(data_root)
    except PropertyConfigError:
        property_config = None
    candidate_sha256 = store.candidate_sha256(candidate)
    guest_photo_path: str | None = None
    guest_photo_sha256: str | None = None
    metadata = summary.metadata
    if metadata.guest_photo_document:
        try:
            guest_photo_sha256 = store.document_sha256(
                case_id, metadata.guest_photo_document
            )
        except ValueError:
            pass
        else:
            guest_photo_path = metadata.guest_photo_document

    plan = compile_fill_plan(
        candidate=candidate,
        property_config=property_config,
        candidate_sha256=candidate_sha256,
        guest_photo_path=guest_photo_path,
        guest_photo_sha256=guest_photo_sha256,
    )
    store.save_fill_plan(case_id, plan)
    return plan


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a self-contained Form C fill plan without portal validation"
    )
    parser.add_argument("case_id")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    args = parser.parse_args()

    print("Preparing fill plan: no browser will open and nothing will be submitted.")
    try:
        plan = prepare_fill_plan(
            store=CaseStore(args.data_dir),
            data_root=args.data_dir,
            case_id=args.case_id,
        )
    except (LookupError, OSError, RuntimeError, ValueError) as error:
        print(f"Fill-plan preparation stopped: {error}")
        raise SystemExit(1) from None

    print(f"Prepared operations: {len(plan.operations)}")
    print(f"Saved {args.data_dir / 'cases' / plan.case_id / 'fill-plan.json'}")


if __name__ == "__main__":
    main()
