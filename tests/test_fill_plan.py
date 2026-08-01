from __future__ import annotations

import json
from datetime import date, time
from pathlib import Path

import pytest

from formc_app.domain import CONDITIONALLY_REQUIRED_FIELD_NAMES, REQUIRED_FORM_C_FIELD_NAMES
from formc_app.dummy_extraction import extract_dummy
from formc_app.fill_plan import (
    BLOCKED_CANDIDATE_FIELDS,
    DATE_FIELDS,
    DERIVED_FIELDS,
    DIRECT_FIELDS,
    NOT_SUBMITTED_FIELDS,
    OPTION_LABEL_FIELDS,
    FillAction,
    FillOptionMatch,
    FillPlanStatus,
    preflight_case,
)
from formc_app.models import CandidateField, CandidateFormC, CaseStatus, FilingRequest, utc_now
from formc_app.portal_catalogue import PortalControl, PortalControlCatalogue, PortalOption
from formc_app.portal_mapping import LIVE_SUBMISSION_CONTROL_IDS
from formc_app.property_config import PropertyConfigError, YerattaPropertyConfig
from formc_app.storage import CaseStore


def _text_control(name: str, ordinal: int) -> PortalControl:
    return PortalControl(
        ordinal=ordinal,
        tag="input",
        name=name,
        element_id=name,
        input_type="text",
    )


def _select_control(
    name: str,
    ordinal: int,
    options: list[tuple[str, str]],
) -> PortalControl:
    return PortalControl(
        ordinal=ordinal,
        tag="select",
        name=name,
        element_id=name,
        options=[PortalOption(label=label, value=value) for label, value in options],
    )


def _radio_control(name: str, ordinal: int, value: str) -> PortalControl:
    return PortalControl(
        ordinal=ordinal,
        tag="input",
        name=name,
        element_id=f"{name}-{value}",
        input_type="radio",
        choice_value=value,
    )


def _catalogue() -> PortalControlCatalogue:
    controls: list[PortalControl] = []
    text_names = (
        list(DIRECT_FIELDS.values())
        + list(DATE_FIELDS.values())
        + list(DERIVED_FIELDS.values())
        + [
            "applicant_dob",
            "applicant_timeoarrivalhotel",
            "applicant_next_destination_place_IN",
        ]
    )
    for name in text_names:
        controls.append(_text_control(name, len(controls)))

    option_controls = {
        "dobformat": [("Complete date", "DY")],
        "applicant_nationality": [("SINGAPORE", "SGP")],
        "applicant_permcountry": [("Singapore", "SGP")],
        "passport_issue_country": [("SINGAPORE", "SGP")],
        "visa_issue_country": [("SINGAPORE", "SGP")],
        "applicant_visatype": [("e-Tourist", "ET")],
        "applicant_arrivedfromcountry": [("India", "IND")],
        "applicant_purpovisit": [("Tourism", "16")],
        "applicant_next_destination_state_IN": [
            ("ANDAMAN AND NICOBAR ISLANDS", "35")
        ],
        "applicant_next_destination_city_district_IN": [("Select", "")],
        "applicant_refstate": [("ANDAMAN AND NICOBAR ISLANDS", "1")],
        "applicant_refstatedistr": [("Select", "")],
    }
    for name, options in option_controls.items():
        controls.append(_select_control(name, len(controls), options))

    for value in ("M", "F", "X"):
        controls.append(_radio_control("applicant_sex", len(controls), value))
    for value in ("Y", "N"):
        controls.append(_radio_control("employed", len(controls), value))
    for value in ("I", "O"):
        controls.append(
            _radio_control("applicant_next_dest_country_flag_r", len(controls), value)
        )
    controls.append(
        PortalControl(
            ordinal=len(controls),
            tag="textarea",
            name="applicant_refaddr",
            element_id="applicant_refaddr",
        )
    )
    controls.append(_text_control("applicant_refpincode", len(controls)))
    controls.append(
        PortalControl(
            ordinal=len(controls),
            tag="input",
            name="file1",
            element_id="file1",
            input_type="file",
        )
    )

    return PortalControlCatalogue(
        portal_location="https://indianfrro.gov.in/frro/FormC/formc.jsp",
        control_count=len(controls),
        controls=controls,
    )


def _ready_case(store: CaseStore) -> str:
    metadata = store.create_case(
        check_in_date=date(2026, 7, 31),
        check_out_date=date(2026, 8, 3),
        arrival_time_hotel=time(14, 25),
        room="Sea 04",
        dummy_profile="daniel",
    )
    fields = extract_dummy("daniel")
    fields.update(
        {
            "permanent_address": CandidateField(
                value="12 Example Street", source="guest_answer"
            ),
            "permanent_city": CandidateField(value="Singapore", source="guest_answer"),
            "permanent_country": CandidateField(value="Singapore", source="guest_answer"),
            "arrived_from_country": CandidateField(value="India", source="guest_answer"),
            "arrived_from_city": CandidateField(value="Port Blair", source="guest_answer"),
            "arrived_from_place": CandidateField(
                value="Veer Savarkar Airport", source="guest_answer"
            ),
            "arrival_date_india": CandidateField(
                value="2026-07-30", source="guest_answer"
            ),
            "arrival_time_hotel": CandidateField(value="14:25", source="staff"),
            "employed_in_india": CandidateField(value="no", source="guest_answer"),
            "purpose_of_visit": CandidateField(value="tourism", source="guest_answer"),
            "next_destination_scope": CandidateField(
                value="india", source="guest_answer"
            ),
            "next_destination_state": CandidateField(
                value="Andaman and Nicobar Islands", source="guest_answer"
            ),
            "next_destination_city": CandidateField(
                value="South Andaman", source="guest_answer"
            ),
            "next_destination": CandidateField(value="Neil Island", source="guest_answer"),
            "check_out_date": CandidateField(value="2026-08-03", source="staff"),
            "check_in_date": CandidateField(value="2026-07-31", source="staff"),
        }
    )
    candidate = CandidateFormC(
        case_id=metadata.case_id,
        fields=fields,
        guest_confirmed_at=utc_now(),
        validated_at=utc_now(),
    )
    store.save_candidate(candidate)
    guest_photo_path = store.save_document(
        metadata.case_id,
        "guest_photo",
        "guest-photo.jpg",
        b"guest-photo",
    )
    store.save_filing_request(
        FilingRequest(
            case_id=metadata.case_id,
            request_version=2,
            candidate_sha256=store.candidate_sha256(candidate),
            guest_photo_sha256=store.document_sha256(metadata.case_id, guest_photo_path),
            guest_photo_source="guest_camera",
            guest_photo_suitability_confirmed_at=utc_now(),
        )
    )
    store.update_status(metadata.case_id, CaseStatus.READY_FOR_FILING, "Ready")
    return metadata.case_id


def _write_preflight_inputs(data_root: Path, catalogue: PortalControlCatalogue) -> None:
    (data_root / "portal-controls.json").write_text(
        catalogue.model_dump_json(indent=2),
        encoding="utf-8",
    )
    property_config = YerattaPropertyConfig(
        reference_address="Yeratta local test address",
        reference_state_code="1",
        reference_district_code="640",
        reference_pin_code="744211",
    )
    (data_root / "property.json").write_text(
        json.dumps(property_config.model_dump(mode="json")),
        encoding="utf-8",
    )


def test_preflight_builds_a_deterministic_ready_plan_without_a_browser(tmp_path: Path):
    store = CaseStore(tmp_path)
    case_id = _ready_case(store)
    _write_preflight_inputs(tmp_path, _catalogue())

    first = preflight_case(store=store, data_root=tmp_path, case_id=case_id)
    second = preflight_case(store=store, data_root=tmp_path, case_id=case_id)

    assert first == second
    assert first.status == FillPlanStatus.READY
    assert first.live_fill_enabled is True
    assert first.live_submit_enabled is False
    assert first.blockers == []
    assert len(first.operations) == 38
    assert {operation.portal_control for operation in first.operations}.isdisjoint(
        LIVE_SUBMISSION_CONTROL_IDS
    )

    operation_by_target = {
        (operation.source_field, operation.portal_control): operation
        for operation in first.operations
    }
    assert operation_by_target[("candidate.sex", "applicant_sex")].value == "M"
    assert operation_by_target[("candidate.sex", "applicant_sex")].action == FillAction.CHECK_RADIO
    assert operation_by_target[("candidate.employed_in_india", "employed")].value == "N"
    assert operation_by_target[("candidate.purpose_of_visit", "applicant_purpovisit")].value == "16"
    assert operation_by_target[("constant.date_of_birth", "dobformat")].value == "DY"
    assert operation_by_target[("candidate.date_of_birth", "applicant_dob")].value == "17/02/1990"
    assert operation_by_target[("candidate.check_in_date", "applicant_doarrivalhotel")].value == "31/07/2026"
    assert operation_by_target[("candidate.arrival_time_hotel", "applicant_timeoarrivalhotel")].value == "14:25"
    assert operation_by_target[("candidate.check_in_date+candidate.check_out_date", "applicant_intnddurhotel")].value == "3"
    assert operation_by_target[("candidate.nationality", "applicant_nationality")].value == "SGP"
    assert operation_by_target[("property.reference_address", "applicant_refaddr")].value == "Yeratta local test address"
    assert operation_by_target[("property.reference_state_code", "applicant_refstate")].value == "1"
    district = operation_by_target[
        ("property.reference_district_code", "applicant_refstatedistr")
    ]
    assert district.value == "640"
    assert district.runtime_option_check_required is True
    destination_city = operation_by_target[
        ("candidate.next_destination_city", "applicant_next_destination_city_district_IN")
    ]
    assert destination_city.value == "South Andaman"
    assert destination_city.runtime_option_check_required is True
    assert destination_city.option_match == FillOptionMatch.LABEL
    assert operation_by_target[("property.reference_pin_code", "applicant_refpincode")].value == "744211"
    photo = operation_by_target[("filing_request.guest_photo", "file1")]
    assert photo.action == FillAction.UPLOAD_FILE
    assert photo.value == "documents/guest_photo.jpg"
    assert photo.value_sha256 == first.guest_photo_sha256

    persisted = json.loads(
        (tmp_path / "cases" / case_id / "fill-plan.json").read_text("utf-8")
    )
    assert persisted == first.model_dump(mode="json")
    assert (tmp_path / "cases" / case_id / "fill-plan.sha256").is_file()


def test_failed_repreflight_invalidates_an_older_ready_plan(tmp_path: Path):
    store = CaseStore(tmp_path)
    case_id = _ready_case(store)
    _write_preflight_inputs(tmp_path, _catalogue())
    assert preflight_case(
        store=store,
        data_root=tmp_path,
        case_id=case_id,
    ).status == FillPlanStatus.READY

    (tmp_path / "property.json").unlink()
    with pytest.raises(PropertyConfigError, match="property configuration"):
        preflight_case(store=store, data_root=tmp_path, case_id=case_id)

    case_dir = tmp_path / "cases" / case_id
    assert not (case_dir / "fill-plan.json").exists()
    assert not (case_dir / "fill-plan.sha256").exists()


def test_preflight_keeps_unsupported_destination_and_conditional_branches_blocked(
    tmp_path: Path,
):
    store = CaseStore(tmp_path)
    case_id = _ready_case(store)
    _write_preflight_inputs(tmp_path, _catalogue())
    candidate = store.load_candidate(case_id)
    assert candidate is not None
    candidate.fields["next_destination_scope"] = CandidateField(
        value="outside_india", source="guest_answer"
    )
    candidate.fields["visa_subtype"] = CandidateField(
        value="unsupported-subtype", source="guest_answer"
    )
    store.save_candidate(candidate)

    plan = preflight_case(store=store, data_root=tmp_path, case_id=case_id)

    blocker_codes = {blocker.code for blocker in plan.blockers}
    assert plan.status == FillPlanStatus.BLOCKED
    assert plan.live_fill_enabled is False
    assert "filing_request_hash_mismatch" in blocker_codes
    assert "outside_india_destination_not_supported" in blocker_codes
    assert "conditional_branch_not_supported" in blocker_codes


def test_preflight_detects_candidate_tampering_and_invalid_closed_choice(tmp_path: Path):
    store = CaseStore(tmp_path)
    case_id = _ready_case(store)
    _write_preflight_inputs(tmp_path, _catalogue())
    candidate = store.load_candidate(case_id)
    assert candidate is not None
    candidate.fields["sex"] = CandidateField(value="unknown", source="guest_answer")
    store.save_candidate(candidate)

    plan = preflight_case(store=store, data_root=tmp_path, case_id=case_id)

    blocker_codes = {blocker.code for blocker in plan.blockers}
    assert "filing_request_hash_mismatch" in blocker_codes
    assert "candidate_choice_invalid" in blocker_codes
    assert not any(operation.source_field == "candidate.sex" for operation in plan.operations)


def test_preflight_detects_safe_catalogue_drift(tmp_path: Path):
    store = CaseStore(tmp_path)
    case_id = _ready_case(store)
    catalogue = _catalogue()
    catalogue.controls = [
        control for control in catalogue.controls if control.name != "applicant_surname"
    ]
    catalogue.control_count = len(catalogue.controls)
    _write_preflight_inputs(tmp_path, catalogue)

    plan = preflight_case(store=store, data_root=tmp_path, case_id=case_id)

    assert any(
        blocker.code == "catalogue_control_mismatch" and blocker.field == "surname"
        for blocker in plan.blockers
    )
    assert not any(operation.source_field == "candidate.surname" for operation in plan.operations)


def test_preflight_detects_guest_photo_tampering(tmp_path: Path):
    store = CaseStore(tmp_path)
    case_id = _ready_case(store)
    _write_preflight_inputs(tmp_path, _catalogue())
    metadata = store.load_metadata(case_id)
    assert metadata.guest_photo_document is not None
    store.document_path(case_id, metadata.guest_photo_document).write_bytes(b"changed")

    plan = preflight_case(store=store, data_root=tmp_path, case_id=case_id)

    assert any(blocker.code == "guest_photo_hash_mismatch" for blocker in plan.blockers)
    assert not any(operation.action == FillAction.UPLOAD_FILE for operation in plan.operations)


def test_every_candidate_field_has_a_fill_plan_policy():
    classified = (
        set(DIRECT_FIELDS)
        | set(DATE_FIELDS)
        | set(DERIVED_FIELDS)
        | set(OPTION_LABEL_FIELDS)
        | {
            "arrival_time_hotel",
            "date_of_birth",
            "sex",
            "employed_in_india",
            "purpose_of_visit",
            "next_destination_scope",
            "next_destination_state",
            "next_destination_city",
            "next_destination",
        }
        | set(BLOCKED_CANDIDATE_FIELDS)
        | set(CONDITIONALLY_REQUIRED_FIELD_NAMES)
        | NOT_SUBMITTED_FIELDS
    )

    assert set(REQUIRED_FORM_C_FIELD_NAMES) <= classified
    assert classified - set(REQUIRED_FORM_C_FIELD_NAMES) == {
        "next_destination_state",
        "next_destination_city",
        "special_category",
        "visa_subtype",
        "room",
        "form_b_reference",
    }
