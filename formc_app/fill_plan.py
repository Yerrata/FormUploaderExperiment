from __future__ import annotations

import argparse
import json
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from formc_app.domain import REQUIRED_FIELD_NAMES
from formc_app.models import CandidateFormC, CaseStatus
from formc_app.portal_catalogue import PortalControl, PortalControlCatalogue
from formc_app.portal_mapping import (
    EMPLOYMENT_CHOICE_CODES,
    LIVE_SUBMISSION_CONTROL_IDS,
    PROPERTY_CONFIG_PORTAL_CONTROLS,
    PURPOSE_OF_VISIT_CHOICE_CODES,
    SEX_CHOICE_CODES,
)
from formc_app.portal_session import validate_portal_url
from formc_app.property_config import YerattaPropertyConfig, load_property_config
from formc_app.storage import CaseStore


CATALOGUE_FILENAME = "portal-controls.json"


class FillPlanStatus(StrEnum):
    READY = "READY"
    BLOCKED = "BLOCKED"


class FillAction(StrEnum):
    FILL_TEXT = "FILL_TEXT"
    SELECT_OPTION = "SELECT_OPTION"
    CHECK_RADIO = "CHECK_RADIO"


class FillValueSource(StrEnum):
    CANDIDATE = "CANDIDATE"
    PROPERTY_CONFIGURATION = "PROPERTY_CONFIGURATION"
    CONSTANT = "CONSTANT"


class FillOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sequence: int
    source_field: str
    portal_control: str
    action: FillAction
    value: str
    value_source: FillValueSource
    runtime_option_check_required: bool = False


class FillBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    field: str | None = None
    message: str


class PortalFillPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    case_id: str
    candidate_sha256: str
    catalogue_sha256: str
    property_config_sha256: str
    status: FillPlanStatus
    live_fill_enabled: Literal[False] = False
    live_submit_enabled: Literal[False] = False
    operations: list[FillOperation] = Field(default_factory=list)
    blockers: list[FillBlocker] = Field(default_factory=list)


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

BLOCKED_CANDIDATE_FIELDS = {
    "arrival_time_hotel": (
        "arrival_time_format_unverified",
        "The portal's exact accepted hotel-arrival time format has not been verified.",
    ),
    "next_destination": (
        "next_destination_schema_unresolved",
        "The India/outside-India destination branch and dependent controls remain unresolved.",
    ),
    "check_out_date": (
        "intended_stay_units_unresolved",
        "The portal's intended-stay duration units have not been confirmed.",
    ),
    "form_b_reference": (
        "filer_reference_semantics_unresolved",
        "Filerfno has not been proven to mean the physical Form B reference.",
    ),
}

NOT_SUBMITTED_FIELDS = {"room"}

GLOBAL_BLOCKERS = (
    FillBlocker(
        code="special_category_semantics_unresolved",
        message="The normal-case meaning of the required special-category control is unknown.",
    ),
    FillBlocker(
        code="visa_subtype_condition_unresolved",
        message="The visa types that require a subtype and their valid subtype choices are unknown.",
    ),
    FillBlocker(
        code="guest_photo_policy_unresolved",
        message="No approved guest-photo source and suitability policy exists yet.",
    ),
)


def _canonical_bytes(value: BaseModel) -> bytes:
    return (
        json.dumps(value.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _normalized_label(value: str) -> str:
    return " ".join(value.split()).casefold()


class _PlanBuilder:
    def __init__(self, catalogue: PortalControlCatalogue):
        self.catalogue = catalogue
        self.operations: list[FillOperation] = []
        self.blockers: list[FillBlocker] = []

    def block(self, code: str, message: str, *, field: str | None = None) -> None:
        self.blockers.append(FillBlocker(code=code, field=field, message=message))

    def _controls(self, identifier: str) -> list[PortalControl]:
        return [
            control
            for control in self.catalogue.controls
            if control.name == identifier or control.element_id == identifier
        ]

    def _single_control(
        self,
        identifier: str,
        *,
        field: str,
        expected_tag: str | None = None,
    ) -> PortalControl | None:
        controls = self._controls(identifier)
        if len(controls) != 1:
            self.block(
                "catalogue_control_mismatch",
                f"Expected exactly one safe catalogue control named {identifier}; found {len(controls)}.",
                field=field,
            )
            return None
        control = controls[0]
        if control.disabled or control.read_only:
            self.block(
                "catalogue_control_not_writable",
                f"Catalogue control {identifier} is disabled or read-only.",
                field=field,
            )
            return None
        if expected_tag is not None and control.tag != expected_tag:
            self.block(
                "catalogue_control_type_mismatch",
                f"Catalogue control {identifier} is {control.tag}, not {expected_tag}.",
                field=field,
            )
            return None
        return control

    def _append(
        self,
        *,
        field: str,
        control: str,
        action: FillAction,
        value: str,
        source: FillValueSource = FillValueSource.CANDIDATE,
        source_field: str | None = None,
        runtime_option_check_required: bool = False,
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
                runtime_option_check_required=runtime_option_check_required,
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
        portal_control = self._single_control(control, field=field)
        if portal_control is None:
            return
        if portal_control.tag not in {"input", "textarea"}:
            self.block(
                "catalogue_control_type_mismatch",
                f"Catalogue control {control} is not a text-capable control.",
                field=field,
            )
            return
        if portal_control.tag == "input" and portal_control.input_type not in {None, "text"}:
            self.block(
                "catalogue_control_type_mismatch",
                f"Catalogue control {control} cannot receive deterministic text.",
                field=field,
            )
            return
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
        portal_control = self._single_control(
            control,
            field=field,
            expected_tag="select",
        )
        if portal_control is None:
            return
        matches = [
            option
            for option in portal_control.options
            if option.value == value and not option.disabled
        ]
        if len(matches) != 1 or not value:
            self.block(
                "catalogue_option_mismatch",
                f"Control {control} does not have one enabled option with value {value!r}.",
                field=field,
            )
            return
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
        portal_control = self._single_control(
            control,
            field=field,
            expected_tag="select",
        )
        if portal_control is None:
            return
        if not value:
            self.block(
                "property_option_missing",
                f"Locked property value for {field} is empty.",
                field=field,
            )
            return
        self._append(
            field=field,
            control=control,
            action=FillAction.SELECT_OPTION,
            value=value,
            source=FillValueSource.PROPERTY_CONFIGURATION,
            source_field=source_field,
            runtime_option_check_required=True,
        )

    def select_label(self, *, field: str, control: str, label: str) -> None:
        portal_control = self._single_control(
            control,
            field=field,
            expected_tag="select",
        )
        if portal_control is None:
            return
        normalized = _normalized_label(label)
        matches = [
            option
            for option in portal_control.options
            if _normalized_label(option.label) == normalized
            and option.value
            and not option.disabled
        ]
        if len(matches) != 1:
            self.block(
                "catalogue_option_label_mismatch",
                f"Control {control} has {len(matches)} enabled exact label matches for {label!r}.",
                field=field,
            )
            return
        self._append(
            field=field,
            control=control,
            action=FillAction.SELECT_OPTION,
            value=matches[0].value,
        )

    def check_radio(self, *, field: str, control: str, value: str) -> None:
        matches = [
            item
            for item in self._controls(control)
            if item.tag == "input"
            and item.input_type == "radio"
            and item.choice_value == value
            and not item.disabled
            and not item.read_only
        ]
        if len(matches) != 1:
            self.block(
                "catalogue_radio_choice_mismatch",
                f"Radio group {control} has {len(matches)} enabled choices with value {value!r}.",
                field=field,
            )
            return
        self._append(
            field=field,
            control=control,
            action=FillAction.CHECK_RADIO,
            value=value,
        )


def _candidate_value(
    candidate: CandidateFormC,
    field: str,
    builder: _PlanBuilder,
) -> str | None:
    value = candidate.value(field)
    if value is None:
        builder.block(
            "candidate_value_missing",
            f"Candidate field {field} is missing.",
            field=field,
        )
    return value


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
        builder.block(
            "candidate_date_invalid",
            f"Candidate field {field} is not a valid ISO date.",
            field=field,
        )
        return None


def compile_fill_plan(
    *,
    candidate: CandidateFormC,
    catalogue: PortalControlCatalogue,
    property_config: YerattaPropertyConfig,
    candidate_sha256: str,
    envelope_blockers: list[FillBlocker] | None = None,
) -> PortalFillPlan:
    """Compile an inspectable plan without opening or changing a browser."""
    validate_portal_url(catalogue.portal_location)
    builder = _PlanBuilder(catalogue)
    builder.blockers.extend(envelope_blockers or [])

    if catalogue.control_count != len(catalogue.controls):
        builder.block(
            "catalogue_count_mismatch",
            "The catalogue control count does not match its control list.",
        )

    for field, control in DIRECT_FIELDS.items():
        value = _candidate_value(candidate, field, builder)
        if value is not None:
            builder.fill_text(field=field, control=control, value=value)

    for field, control in DATE_FIELDS.items():
        value = _portal_date(candidate, field, builder)
        if value is not None:
            builder.fill_text(field=field, control=control, value=value)

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
        ("sex", "applicant_sex", SEX_CHOICE_CODES, FillAction.CHECK_RADIO),
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
        if portal_value is None:
            builder.block(
                "candidate_choice_invalid",
                f"Candidate field {field} contains an unsupported closed choice.",
                field=field,
            )
        elif action == FillAction.CHECK_RADIO:
            builder.check_radio(field=field, control=control, value=portal_value)
        else:
            builder.select_value(field=field, control=control, value=portal_value)

    for field, (code, message) in BLOCKED_CANDIDATE_FIELDS.items():
        _candidate_value(candidate, field, builder)
        builder.block(code, message, field=field)

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

    builder.blockers.extend(GLOBAL_BLOCKERS)

    planned_or_blocked = (
        set(DIRECT_FIELDS)
        | set(DATE_FIELDS)
        | set(OPTION_LABEL_FIELDS)
        | {"date_of_birth", "sex", "employed_in_india", "purpose_of_visit"}
        | set(BLOCKED_CANDIDATE_FIELDS)
        | NOT_SUBMITTED_FIELDS
    )
    unclassified = set(REQUIRED_FIELD_NAMES) - planned_or_blocked
    for field in sorted(unclassified):
        builder.block(
            "candidate_field_unclassified",
            f"Candidate field {field} has no fill-plan policy.",
            field=field,
        )

    plan = PortalFillPlan(
        case_id=candidate.case_id,
        candidate_sha256=candidate_sha256,
        catalogue_sha256=CaseStore.sha256(_canonical_bytes(catalogue)),
        property_config_sha256=CaseStore.sha256(_canonical_bytes(property_config)),
        status=FillPlanStatus.BLOCKED if builder.blockers else FillPlanStatus.READY,
        operations=builder.operations,
        blockers=builder.blockers,
    )
    return plan


def preflight_case(*, store: CaseStore, data_root: Path, case_id: str) -> PortalFillPlan:
    """Validate the sealed local inputs and atomically persist a non-executable plan."""
    summary = store.get_summary(case_id)
    candidate = summary.candidate
    if candidate is None:
        raise ValueError("Candidate Form C is missing")
    if candidate.case_id != case_id:
        raise ValueError("Candidate case ID does not match its case folder")

    catalogue_path = data_root / CATALOGUE_FILENAME
    try:
        catalogue = PortalControlCatalogue.model_validate_json(
            catalogue_path.read_text(encoding="utf-8")
        )
    except FileNotFoundError as exc:
        raise ValueError(f"Safe portal catalogue is missing: {catalogue_path}") from exc

    property_config = load_property_config(data_root)
    candidate_sha256 = store.candidate_sha256(candidate)
    envelope_blockers: list[FillBlocker] = []
    if summary.state.status != CaseStatus.READY_FOR_FILING:
        envelope_blockers.append(
            FillBlocker(
                code="case_not_ready",
                message=f"Case status is {summary.state.status}, not READY_FOR_FILING.",
            )
        )
    if candidate.guest_confirmed_at is None or candidate.validated_at is None:
        envelope_blockers.append(
            FillBlocker(
                code="candidate_not_confirmed",
                message="The Candidate has not been guest-confirmed and validated.",
            )
        )
    missing = candidate.missing(REQUIRED_FIELD_NAMES)
    if missing:
        envelope_blockers.append(
            FillBlocker(
                code="candidate_incomplete",
                message=f"Candidate is missing required fields: {', '.join(missing)}.",
            )
        )
    filing_request = store.load_filing_request(case_id)
    if filing_request is None:
        envelope_blockers.append(
            FillBlocker(
                code="filing_request_missing",
                message="The sealed Filing Request is missing.",
            )
        )
    elif filing_request.case_id != case_id:
        envelope_blockers.append(
            FillBlocker(
                code="filing_request_case_id_mismatch",
                message="The Filing Request case ID does not match its case folder.",
            )
        )
    elif filing_request.candidate_sha256 != candidate_sha256:
        envelope_blockers.append(
            FillBlocker(
                code="filing_request_hash_mismatch",
                message="Candidate content no longer matches the sealed Filing Request.",
            )
        )

    plan = compile_fill_plan(
        candidate=candidate,
        catalogue=catalogue,
        property_config=property_config,
        candidate_sha256=candidate_sha256,
        envelope_blockers=envelope_blockers,
    )
    store.save_fill_plan(case_id, plan)
    return plan


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a deterministic, non-browser Form C fill plan"
    )
    parser.add_argument("case_id")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    args = parser.parse_args()

    print("Offline preflight only: no browser will open and no form will be filled or submitted.")
    try:
        plan = preflight_case(
            store=CaseStore(args.data_dir),
            data_root=args.data_dir,
            case_id=args.case_id,
        )
    except (LookupError, OSError, RuntimeError, ValueError) as error:
        print(f"Fill-plan preflight stopped safely: {error}")
        raise SystemExit(1) from None

    print(f"Fill plan: {plan.status}")
    print(f"Prepared operations: {len(plan.operations)}")
    for blocker in plan.blockers:
        location = f" [{blocker.field}]" if blocker.field else ""
        print(f"Blocked: {blocker.code}{location} — {blocker.message}")
    print(f"Saved {args.data_dir / 'cases' / plan.case_id / 'fill-plan.json'}")
    if plan.status == FillPlanStatus.BLOCKED:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
