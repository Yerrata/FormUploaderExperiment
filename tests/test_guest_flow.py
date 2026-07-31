from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from formc_app.domain import (
    EXTRACTED_FIELD_NAMES,
    QUESTION_FIELD_NAMES,
    REQUIRED_FIELD_NAMES,
)
from formc_app.main import create_app
from formc_app.models import CaseStatus
from formc_app.storage import CaseStore, InvalidGuestTokenError


def create_case(client: TestClient, app, *, profile: str = "daniel"):
    response = client.post(
        "/staff/cases",
        data={
            "check_in_date": "2026-07-31",
            "check_out_date": "2026-08-03",
            "room": "Sea 04",
            "form_b_reference": "B-2026-118",
            "dummy_profile": profile,
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    return app.state.store.list_cases()[-1]


GUEST_ANSWERS = {
    "permanent_address": "12 Example Street",
    "permanent_city": "Singapore",
    "permanent_country": "Singapore",
    "arrived_from_country": "India",
    "arrived_from_city": "Port Blair",
    "arrived_from_place": "Veer Savarkar Airport",
    "arrival_date_india": "2026-07-30",
    "arrival_time_hotel": "14:25",
    "employed_in_india": "no",
    "purpose_of_visit": "tourism",
    "next_destination": "Neil Island",
    "check_out_date": "2026-08-03",
}


def test_complete_guest_flow_creates_one_validated_filing_request(tmp_path: Path):
    app = create_app(tmp_path)
    client = TestClient(app, follow_redirects=False)
    created = create_case(client, app)
    token = created.metadata.guest_token

    capture = client.post(
        f"/guest/{token}/capture",
        files={
            "passport": ("passport.jpg", b"passport-photo", "image/jpeg"),
            "visa": ("visa.jpg", b"visa-photo", "image/jpeg"),
        },
    )
    assert capture.status_code == 303
    candidate = app.state.store.load_candidate(created.metadata.case_id)
    assert candidate is not None

    review_values = {
        name: candidate.value(name)
        for name in EXTRACTED_FIELD_NAMES
    }
    review_values["passport_number"] = "GUEST-CORRECTED-001"
    review = client.post(f"/guest/{token}/review", data=review_values)
    assert review.status_code == 303

    first_question = client.get(f"/guest/{token}/question")
    assert first_question.status_code == 200
    assert "permanently reside" in first_question.text.lower()
    for field_name in QUESTION_FIELD_NAMES:
        current = app.state.store.load_candidate(created.metadata.case_id)
        assert current is not None
        if current.value(field_name):
            continue
        assert client.post(
            f"/guest/{token}/question",
            data={"field_name": field_name, "answer": GUEST_ANSWERS[field_name]},
        ).status_code == 303

    confirm = client.get(f"/guest/{token}/confirm")
    assert confirm.status_code == 200
    assert "GUEST-CORRECTED-001" in confirm.text
    assert client.post(f"/guest/{token}/confirm").status_code == 303

    summary = app.state.store.get_summary(created.metadata.case_id)
    assert summary.state.status == CaseStatus.READY_FOR_FILING
    assert summary.candidate is not None
    correction = summary.candidate.fields["passport_number"]
    assert correction.source == "guest_correction"
    assert correction.original_value == "E12345884"
    assert (tmp_path / "cases" / created.metadata.case_id / "filing-request.json").is_file()
    assert (tmp_path / "cases" / created.metadata.case_id / "documents" / "passport.jpg").read_bytes() == b"passport-photo"
    assert client.get(f"/guest/{token}/done").status_code == 200
    assert client.get(f"/guest/{token}/review").status_code == 403


def test_closed_guest_choice_rejects_an_unknown_value(tmp_path: Path):
    app = create_app(tmp_path)
    client = TestClient(app, follow_redirects=False)
    created = create_case(client, app)
    token = created.metadata.guest_token
    client.post(
        f"/guest/{token}/capture",
        files={
            "passport": ("passport.jpg", b"passport", "image/jpeg"),
            "visa": ("visa.jpg", b"visa", "image/jpeg"),
        },
    )
    candidate = app.state.store.load_candidate(created.metadata.case_id)
    assert candidate is not None
    review_values = {name: candidate.value(name) for name in EXTRACTED_FIELD_NAMES}
    assert client.post(f"/guest/{token}/review", data=review_values).status_code == 303

    response = client.post(
        f"/guest/{token}/question",
        data={"field_name": "employed_in_india", "answer": "sometimes"},
    )

    assert response.status_code == 422

    invalid_time = client.post(
        f"/guest/{token}/question",
        data={"field_name": "arrival_time_hotel", "answer": "25:90"},
    )
    assert invalid_time.status_code == 422


def test_missing_document_and_missing_answer_block_progress(tmp_path: Path):
    app = create_app(tmp_path)
    client = TestClient(app, follow_redirects=False)
    created = create_case(client, app)
    token = created.metadata.guest_token

    response = client.post(
        f"/guest/{token}/capture",
        files={
            "passport": ("passport.jpg", b"passport", "image/jpeg"),
            "visa": ("visa.jpg", b"", "image/jpeg"),
        },
    )
    assert response.status_code == 400
    assert app.state.store.load_candidate(created.metadata.case_id) is None


def test_guest_token_is_single_case_and_expires(tmp_path: Path):
    store = CaseStore(tmp_path)
    first = store.create_case(
        check_in_date=date(2026, 7, 31),
        check_out_date=date(2026, 8, 2),
        room="One",
        form_b_reference="B-1",
        dummy_profile="daniel",
    )
    second = store.create_case(
        check_in_date=date(2026, 7, 31),
        check_out_date=date(2026, 8, 2),
        room="Two",
        form_b_reference="B-2",
        dummy_profile="elena",
    )
    assert store.require_guest_token(first.guest_token).metadata.case_id == first.case_id
    assert store.require_guest_token(first.guest_token).metadata.case_id != second.case_id

    expired = store.create_case(
        check_in_date=date(2026, 7, 31),
        check_out_date=None,
        room="Three",
        form_b_reference="B-3",
        dummy_profile="aiko",
        token_lifetime=timedelta(seconds=-1),
    )
    try:
        store.require_guest_token(expired.guest_token)
    except InvalidGuestTokenError as error:
        assert "expired" in str(error)
    else:
        raise AssertionError("Expired Guest Session was accepted")


def test_dashboard_and_case_pages_render_on_mobile_first_app(tmp_path: Path):
    app = create_app(tmp_path)
    client = TestClient(app)
    created = create_case(client, app)
    dashboard = client.get("/staff?check_in_date=2026-07-31")
    assert dashboard.status_code == 200
    assert "Outstanding cases" in dashboard.text
    detail = client.get(f"/staff/cases/{created.metadata.case_id}")
    assert detail.status_code == 200
    assert "Government site" in detail.text


def test_mock_portal_reuses_identical_ack_and_rejects_conflicting_duplicate(tmp_path: Path):
    app = create_app(tmp_path)
    client = TestClient(app, follow_redirects=False)
    created = create_case(client, app, profile="aiko")
    values = {name: f"value-{name}" for name in REQUIRED_FIELD_NAMES}

    first = client.post(
        f"/mock-government/form-c/{created.metadata.case_id}",
        data=values,
    )
    assert first.status_code == 200
    acknowledgement = app.state.store.load_mock_submission(
        created.metadata.case_id
    ).acknowledgement
    assert acknowledgement in first.text

    repeated = client.post(
        f"/mock-government/form-c/{created.metadata.case_id}",
        data=values,
    )
    assert repeated.status_code == 200
    assert acknowledgement in repeated.text

    conflicting = dict(values)
    conflicting["passport_number"] = "DIFFERENT"
    rejected = client.post(
        f"/mock-government/form-c/{created.metadata.case_id}",
        data=conflicting,
    )
    assert rejected.status_code == 409


def test_only_safe_pre_submit_failure_can_return_to_queue(tmp_path: Path):
    app = create_app(tmp_path)
    client = TestClient(app, follow_redirects=False)
    created = create_case(client, app)
    app.state.store.update_status(
        created.metadata.case_id,
        CaseStatus.BLOCKED,
        "Browser failed before submission",
    )
    retried = client.post(f"/staff/cases/{created.metadata.case_id}/retry")
    assert retried.status_code == 303
    assert app.state.store.load_state(created.metadata.case_id).status == CaseStatus.READY_FOR_FILING
    refused = client.post(f"/staff/cases/{created.metadata.case_id}/retry")
    assert refused.status_code == 409
