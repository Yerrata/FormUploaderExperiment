from __future__ import annotations

import json
from datetime import date, time
from pathlib import Path

from formc_app.dummy_extraction import extract_dummy
from formc_app.fill_plan import (
    FillAction,
    FillOptionMatch,
    FillPlanStatus,
    prepare_fill_plan,
)
from formc_app.models import CandidateField, CandidateFormC, CaseStatus, utc_now
from formc_app.portal_mapping import LIVE_SUBMISSION_CONTROL_IDS
from formc_app.property_config import YerattaPropertyConfig
from formc_app.storage import CaseStore


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
            "arrived_from_country": CandidateField(value="Singapore", source="guest_answer"),
            "arrived_from_city": CandidateField(value="Singapore", source="guest_answer"),
            "arrived_from_place": CandidateField(
                value="Changi Airport", source="guest_answer"
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
    store.save_document(
        metadata.case_id,
        "guest_photo",
        "guest-photo.jpg",
        b"guest-photo",
    )
    store.update_status(metadata.case_id, CaseStatus.READY_FOR_FILING, "Ready")
    return metadata.case_id


def _write_property_config(data_root: Path) -> None:
    config = YerattaPropertyConfig(
        reference_address="Yeratta local test address",
        reference_state_code="1",
        reference_district_code="640",
        reference_pin_code="744211",
    )
    (data_root / "property.json").write_text(
        json.dumps(config.model_dump(mode="json")), encoding="utf-8"
    )


def test_prepare_fill_plan_is_self_contained_and_catalogue_free(tmp_path: Path):
    store = CaseStore(tmp_path)
    case_id = _ready_case(store)
    _write_property_config(tmp_path)

    first = prepare_fill_plan(store=store, data_root=tmp_path, case_id=case_id)
    second = prepare_fill_plan(store=store, data_root=tmp_path, case_id=case_id)

    assert first == second
    assert first.status == FillPlanStatus.READY
    assert first.live_fill_enabled is True
    assert first.live_submit_enabled is False
    assert first.blockers == []
    assert first.catalogue_sha256 is None
    assert first.property_config_sha256 is None
    assert {operation.portal_control for operation in first.operations}.isdisjoint(
        LIVE_SUBMISSION_CONTROL_IDS
    )

    operations = {
        (operation.source_field, operation.portal_control): operation
        for operation in first.operations
    }
    assert operations[("candidate.sex", "applicant_sex")].value == "M"
    assert operations[("candidate.visa_type", "applicant_visatype")].value == "TOURIST VISA"
    assert operations[("candidate.visa_type", "applicant_visatype")].option_match == FillOptionMatch.LABEL
    assert operations[("candidate.employed_in_india", "employed")].value == "N"
    assert operations[("candidate.purpose_of_visit", "applicant_purpovisit")].value == "16"
    assert operations[
        ("candidate.next_destination_state", "applicant_next_destination_state_IN")
    ].value == "1"
    assert operations[
        ("candidate.next_destination_state", "applicant_next_destination_state_IN")
    ].option_match == FillOptionMatch.VALUE
    assert operations[("candidate.date_of_birth", "applicant_dob")].value == "17/02/1990"
    assert operations[("candidate.check_in_date", "applicant_doarrivalhotel")].value == "31/07/2026"
    assert operations[("candidate.check_in_date+candidate.check_out_date", "applicant_intnddurhotel")].value == "3"
    assert operations[("candidate.nationality", "applicant_nationality")].value == "SINGAPORE"
    assert operations[("property.reference_address", "applicant_refaddr")].value == "Yeratta local test address"
    assert operations[("property.reference_district_code", "applicant_refstatedistr")].runtime_option_check_required is True
    assert operations[("filing_request.guest_photo", "file1")].action == FillAction.UPLOAD_FILE

    persisted = json.loads(
        (tmp_path / "cases" / case_id / "fill-plan.json").read_text("utf-8")
    )
    assert persisted == first.model_dump(mode="json")
    assert (tmp_path / "cases" / case_id / "fill-plan.sha256").is_file()


def test_missing_property_and_catalogue_do_not_block_plan_creation(tmp_path: Path):
    store = CaseStore(tmp_path)
    case_id = _ready_case(store)

    plan = prepare_fill_plan(store=store, data_root=tmp_path, case_id=case_id)

    assert plan.status == FillPlanStatus.READY
    assert plan.blockers == []
    assert not any(
        operation.value_source == "PROPERTY_CONFIGURATION"
        for operation in plan.operations
    )


def test_business_values_are_copied_without_preflight_rejection(tmp_path: Path):
    store = CaseStore(tmp_path)
    case_id = _ready_case(store)
    candidate = store.load_candidate(case_id)
    assert candidate is not None
    candidate.fields["sex"] = CandidateField(value="unknown", source="guest_answer")
    candidate.fields["visa_type"] = CandidateField(
        value="e-Tourist", source="guest_correction"
    )
    candidate.fields["arrived_from_country"] = CandidateField(
        value="asd", source="guest_answer"
    )
    candidate.fields["next_destination_scope"] = CandidateField(
        value="outside_india", source="guest_answer"
    )
    candidate.fields["visa_subtype"] = CandidateField(
        value="unsupported-subtype", source="guest_answer"
    )
    candidate.fields["check_out_date"] = CandidateField(
        value="not-a-date", source="guest_answer"
    )
    store.save_candidate(candidate)

    plan = prepare_fill_plan(store=store, data_root=tmp_path, case_id=case_id)

    operations = {operation.source_field: operation for operation in plan.operations}
    assert plan.status == FillPlanStatus.READY
    assert plan.blockers == []
    assert operations["candidate.sex"].value == "unknown"
    assert operations["candidate.visa_type"].value == "e-Tourist"
    assert operations["candidate.arrived_from_country"].value == "asd"
    assert operations["candidate.next_destination_scope"].value == "O"


def test_changed_guest_photo_is_copied_into_a_fresh_plan(tmp_path: Path):
    store = CaseStore(tmp_path)
    case_id = _ready_case(store)
    metadata = store.load_metadata(case_id)
    assert metadata.guest_photo_document is not None
    store.document_path(case_id, metadata.guest_photo_document).write_bytes(b"changed")

    plan = prepare_fill_plan(store=store, data_root=tmp_path, case_id=case_id)

    photo = next(
        operation
        for operation in plan.operations
        if operation.action == FillAction.UPLOAD_FILE
    )
    assert photo.value_sha256 == store.document_sha256(
        case_id, metadata.guest_photo_document
    )
