from __future__ import annotations

from datetime import date, time, timedelta
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from formc_app.domain import (
    EXTRACTED_FIELD_NAMES,
    GUEST_QUESTION_FIELD_NAMES,
    REQUIRED_FORM_C_FIELD_NAMES,
    guest_question_field_names,
)
from formc_app.dummy_extraction import DUMMY_PROFILES
from formc_app.main import PORTAL_QUESTION_CONTROLS, create_app
from formc_app.models import CandidateField, CaseStatus
from formc_app.portal_catalogue import (
    PortalControl,
    PortalControlCatalogue,
    PortalOption,
)
from formc_app.storage import CaseStore, InvalidGuestTokenError


def guest_photo_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (640, 800), color=(80, 120, 160)).save(output, format="JPEG")
    return output.getvalue()


def capture_files(*, visa: bytes = b"visa-photo"):
    return {
        "passport": ("passport.jpg", b"passport-photo", "image/jpeg"),
        "visa": ("visa.jpg", visa, "image/jpeg"),
        "guest_photo": ("guest.jpg", guest_photo_bytes(), "image/jpeg"),
    }


def create_case(
    client: TestClient,
    app,
    *,
    profile: str = "daniel",
    check_out_date: str | None = "2026-08-03",
):
    if not (app.state.store.root / "portal-controls.json").exists():
        write_country_catalogue(app.state.store.root)
    staff_values = {
        "check_in_date": "2026-07-31",
        "arrival_time_hotel": "14:25",
        "room": "Sea 04",
        "dummy_profile": profile,
    }
    if check_out_date is not None:
        staff_values["check_out_date"] = check_out_date
    response = client.post(
        "/staff/cases",
        data=staff_values,
        follow_redirects=False,
    )
    assert response.status_code == 303
    return app.state.store.list_cases()[-1]


GUEST_ANSWERS = {
    "permanent_address": "12 Example Street",
    "permanent_city": "Singapore",
    "permanent_country": "Singapore",
    "arrived_from_country": "SINGAPORE",
    "arrived_from_city": "Singapore",
    "arrived_from_place": "Changi Airport",
    "arrival_date_india": "2026-07-30",
    "employed_in_india": "no",
    "purpose_of_visit": "tourism",
    "next_destination_scope": "india",
    "next_destination_state": "Andaman and Nicobar Islands",
    "next_destination_city": "South Andaman",
    "next_destination": "Neil Island",
    "check_out_date": "2026-08-03",
}


def write_country_catalogue(data_root: Path) -> None:
    write_choice_catalogue(
        data_root,
        "applicant_arrivedfromcountry",
        (("SINGAPORE", "SGP"), ("UNITED KINGDOM", "GBR")),
    )


def write_choice_catalogue(
    data_root: Path,
    control_name: str,
    choices: tuple[tuple[str, str], ...],
) -> None:
    catalogue = PortalControlCatalogue(
        portal_location="https://indianfrro.gov.in/frro/FormC/formc.jsp",
        control_count=1,
        controls=[
            PortalControl(
                ordinal=0,
                tag="select",
                name=control_name,
                element_id=control_name,
                options=[PortalOption(label="Select", value="")]
                + [
                    PortalOption(label=label, value=value)
                    for label, value in choices
                ],
            )
        ],
    )
    (data_root / "portal-controls.json").write_text(
        catalogue.model_dump_json(indent=2),
        encoding="utf-8",
    )


def test_complete_guest_flow_creates_one_validated_filing_request(tmp_path: Path):
    app = create_app(tmp_path)
    client = TestClient(app, follow_redirects=False)
    created = create_case(client, app)
    token = created.metadata.guest_token

    capture = client.post(
        f"/guest/{token}/capture",
        files=capture_files(),
        data={"guest_photo_confirmed": "yes"},
    )
    assert capture.status_code == 303
    candidate = app.state.store.load_candidate(created.metadata.case_id)
    assert candidate is not None
    assert candidate.value("arrival_time_hotel") == "14:25"
    assert candidate.fields["arrival_time_hotel"].source == "staff"
    assert "room" not in candidate.fields
    assert "form_b_reference" not in candidate.fields
    assert candidate.value("permanent_address") == "12 EXAMPLE STREET"
    assert candidate.fields["permanent_address"].source == "passport_dummy"

    review_page = client.get(f"/guest/{token}/review")
    assert review_page.status_code == 200
    assert "12 EXAMPLE STREET" in review_page.text
    assert "already filled" in review_page.text.lower()

    review_values = {
        name: candidate.value(name)
        for name in EXTRACTED_FIELD_NAMES
    }
    review_values["passport_number"] = "GUEST-CORRECTED-001"
    review_values["permanent_address"] = "99 Corrected Home Road"
    review = client.post(f"/guest/{token}/review", data=review_values)
    assert review.status_code == 303

    first_question = client.get(f"/guest/{token}/question")
    assert first_question.status_code == 200
    assert "arrive from immediately" in first_question.text.lower()
    assert "permanent home address" not in first_question.text.lower()
    assert "arrival_time_hotel" not in GUEST_QUESTION_FIELD_NAMES
    for field_name in GUEST_ANSWERS:
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
    address_correction = summary.candidate.fields["permanent_address"]
    assert address_correction.source == "guest_correction"
    assert address_correction.original_value == "12 EXAMPLE STREET"
    assert address_correction.value == "99 Corrected Home Road"
    assert (tmp_path / "cases" / created.metadata.case_id / "filing-request.json").is_file()
    passport = (
        tmp_path
        / "cases"
        / created.metadata.case_id
        / "documents"
        / "passport.jpg"
    )
    assert passport.read_bytes() == b"passport-photo"
    guest_photo = tmp_path / "cases" / created.metadata.case_id / "documents" / "guest_photo.jpg"
    assert guest_photo.read_bytes().startswith(b"\xff\xd8")
    assert guest_photo.stat().st_size <= 1_000_000
    filing_request = app.state.store.load_filing_request(created.metadata.case_id)
    assert filing_request is not None
    assert filing_request.request_version == 2
    assert filing_request.guest_photo_sha256 == app.state.store.sha256(
        guest_photo.read_bytes()
    )
    assert client.get(f"/guest/{token}/done").status_code == 200
    assert client.get(f"/guest/{token}/review").status_code == 403


def test_arrived_from_country_is_restricted_to_live_catalogue_options(
    tmp_path: Path,
):
    write_country_catalogue(tmp_path)
    app = create_app(tmp_path)
    client = TestClient(app, follow_redirects=False)
    created = create_case(client, app)
    token = created.metadata.guest_token
    client.post(
        f"/guest/{token}/capture",
        files=capture_files(),
        data={"guest_photo_confirmed": "yes"},
    )
    candidate = app.state.store.load_candidate(created.metadata.case_id)
    assert candidate is not None
    review_values = {name: candidate.value(name) for name in EXTRACTED_FIELD_NAMES}
    assert client.post(f"/guest/{token}/review", data=review_values).status_code == 303

    question = client.get(f"/guest/{token}/question")
    assert question.status_code == 200
    assert '<select class="answer-input" name="answer"' in question.text
    assert '<option value="SINGAPORE">SINGAPORE</option>' in question.text
    assert '<option value="UNITED KINGDOM">UNITED KINGDOM</option>' in question.text

    rejected = client.post(
        f"/guest/{token}/question",
        data={"field_name": "arrived_from_country", "answer": "asd"},
    )
    assert rejected.status_code == 422
    candidate = app.state.store.load_candidate(created.metadata.case_id)
    assert candidate is not None
    assert candidate.value("arrived_from_country") is None

    accepted = client.post(
        f"/guest/{token}/question",
        data={"field_name": "arrived_from_country", "answer": "SINGAPORE"},
    )
    assert accepted.status_code == 303


def test_portal_owned_question_falls_back_to_text_without_a_catalogue(
    tmp_path: Path,
):
    app = create_app(tmp_path)
    client = TestClient(app, follow_redirects=False)
    created = create_case(client, app)
    token = created.metadata.guest_token
    client.post(
        f"/guest/{token}/capture",
        files=capture_files(),
        data={"guest_photo_confirmed": "yes"},
    )
    candidate = app.state.store.load_candidate(created.metadata.case_id)
    assert candidate is not None
    review_values = {name: candidate.value(name) for name in EXTRACTED_FIELD_NAMES}
    assert client.post(f"/guest/{token}/review", data=review_values).status_code == 303
    (tmp_path / "portal-controls.json").unlink()

    question = client.get(f"/guest/{token}/question")
    assert question.status_code == 200
    assert 'class="answer-input" type="text" name="answer"' in question.text
    accepted = client.post(
        f"/guest/{token}/question",
        data={"field_name": "arrived_from_country", "answer": "asd"},
    )
    assert accepted.status_code == 303
    updated = app.state.store.load_candidate(created.metadata.case_id)
    assert updated is not None
    assert updated.value("arrived_from_country") == "asd"


@pytest.mark.parametrize(
    "field_name",
    tuple(PORTAL_QUESTION_CONTROLS),
)
def test_every_captured_portal_enum_renders_as_an_additional_question_combo(
    tmp_path: Path,
    field_name: str,
):
    control_name = PORTAL_QUESTION_CONTROLS[field_name]
    write_choice_catalogue(tmp_path, control_name, (("Accepted choice", "A1"),))
    app = create_app(tmp_path)
    client = TestClient(app, follow_redirects=False)
    created = create_case(client, app)
    token = created.metadata.guest_token
    client.post(
        f"/guest/{token}/capture",
        files=capture_files(),
        data={"guest_photo_confirmed": "yes"},
    )
    candidate = app.state.store.load_candidate(created.metadata.case_id)
    assert candidate is not None
    candidate.fields["next_destination_scope"] = CandidateField(
        value="india", source="guest_answer"
    )
    for name in guest_question_field_names(
        {candidate_name: field.value for candidate_name, field in candidate.fields.items()}
    ):
        if name == field_name or candidate.value(name):
            continue
        candidate.fields[name] = CandidateField(
            value=GUEST_ANSWERS[name], source="guest_answer"
        )
    candidate.fields.pop(field_name, None)
    app.state.store.save_candidate(candidate)

    question = client.get(f"/guest/{token}/question")

    assert question.status_code == 200
    assert f'name="field_name" value="{field_name}"' in question.text
    assert '<select class="answer-input" name="answer"' in question.text
    assert '<option value="Accepted choice">Accepted choice</option>' in question.text


def test_guest_is_asked_for_checkout_only_when_staff_did_not_supply_it(
    tmp_path: Path,
):
    app = create_app(tmp_path)
    client = TestClient(app, follow_redirects=False)
    created = create_case(client, app, check_out_date=None)
    token = created.metadata.guest_token
    client.post(
        f"/guest/{token}/capture",
        files=capture_files(),
        data={"guest_photo_confirmed": "yes"},
    )
    candidate = app.state.store.load_candidate(created.metadata.case_id)
    assert candidate is not None
    review_values = {name: candidate.value(name) for name in EXTRACTED_FIELD_NAMES}
    assert client.post(f"/guest/{token}/review", data=review_values).status_code == 303

    for field_name in GUEST_ANSWERS:
        if field_name == "check_out_date":
            continue
        current = app.state.store.load_candidate(created.metadata.case_id)
        assert current is not None
        if current.value(field_name):
            continue
        assert client.post(
            f"/guest/{token}/question",
            data={"field_name": field_name, "answer": GUEST_ANSWERS[field_name]},
        ).status_code == 303

    checkout_question = client.get(f"/guest/{token}/question")
    assert checkout_question.status_code == 200
    assert "expect to check out" in checkout_question.text.lower()


def test_missing_extracted_document_fields_fall_back_to_guest_questions(
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.setitem(
        DUMMY_PROFILES["daniel"],
        "permanent_address",
        (None, "passport_dummy"),
    )
    monkeypatch.setitem(
        DUMMY_PROFILES["daniel"],
        "passport_number",
        (None, "passport_dummy"),
    )
    monkeypatch.setitem(
        DUMMY_PROFILES["daniel"],
        "visa_number",
        (None, "visa_dummy"),
    )
    app = create_app(tmp_path)
    client = TestClient(app, follow_redirects=False)
    created = create_case(client, app)
    token = created.metadata.guest_token
    client.post(
        f"/guest/{token}/capture",
        files=capture_files(),
        data={"guest_photo_confirmed": "yes"},
    )
    candidate = app.state.store.load_candidate(created.metadata.case_id)
    assert candidate is not None
    review_values = {
        name: candidate.value(name)
        for name in EXTRACTED_FIELD_NAMES
        if candidate.value(name)
    }
    review_page = client.get(f"/guest/{token}/review")
    assert "Passport number" not in review_page.text
    assert "Visa number" not in review_page.text
    assert client.post(f"/guest/{token}/review", data=review_values).status_code == 303

    questions_and_answers = (
        ("permanent home address", "12 Example Street", "permanent_address"),
        ("passport number", "P-MISSING-1", "passport_number"),
        ("visa number", "V-MISSING-1", "visa_number"),
    )
    for expected_text, answer, field_name in questions_and_answers:
        question = client.get(f"/guest/{token}/question")
        assert expected_text in question.text.lower()
        assert client.post(
            f"/guest/{token}/question",
            data={"field_name": field_name, "answer": answer},
        ).status_code == 303

    updated = app.state.store.load_candidate(created.metadata.case_id)
    assert updated is not None
    assert updated.fields["permanent_address"].source == "guest_answer"
    assert updated.fields["passport_number"].source == "guest_answer"
    assert updated.fields["visa_number"].source == "guest_answer"


def test_closed_guest_choice_rejects_an_unknown_value(tmp_path: Path):
    app = create_app(tmp_path)
    client = TestClient(app, follow_redirects=False)
    created = create_case(client, app)
    token = created.metadata.guest_token
    client.post(
        f"/guest/{token}/capture",
        files=capture_files(),
        data={"guest_photo_confirmed": "yes"},
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

    unsupported_arrival_time_question = client.post(
        f"/guest/{token}/question",
        data={"field_name": "arrival_time_hotel", "answer": "25:90"},
    )
    assert unsupported_arrival_time_question.status_code == 400


@pytest.mark.parametrize(
    ("submitted_answer", "stored_value"),
    (
        ("yes", "yes"),
        ("Yes", "yes"),
        ("Y", "yes"),
        ("no", "no"),
        ("No", "no"),
        ("N", "no"),
    ),
)
def test_employment_choice_values_labels_and_portal_codes_are_canonicalised(
    tmp_path: Path,
    submitted_answer: str,
    stored_value: str,
):
    app = create_app(tmp_path)
    client = TestClient(app, follow_redirects=False)
    created = create_case(client, app)
    token = created.metadata.guest_token
    client.post(
        f"/guest/{token}/capture",
        files=capture_files(),
        data={"guest_photo_confirmed": "yes"},
    )
    candidate = app.state.store.load_candidate(created.metadata.case_id)
    assert candidate is not None
    review_values = {name: candidate.value(name) for name in EXTRACTED_FIELD_NAMES}
    assert client.post(f"/guest/{token}/review", data=review_values).status_code == 303

    response = client.post(
        f"/guest/{token}/question",
        data={
            "field_name": "employed_in_india",
            "answer": submitted_answer,
        },
    )

    assert response.status_code == 303
    updated = app.state.store.load_candidate(created.metadata.case_id)
    assert updated is not None
    assert updated.value("employed_in_india") == stored_value


def test_missing_document_and_missing_answer_block_progress(tmp_path: Path):
    app = create_app(tmp_path)
    client = TestClient(app, follow_redirects=False)
    created = create_case(client, app)
    token = created.metadata.guest_token

    response = client.post(
        f"/guest/{token}/capture",
        files=capture_files(visa=b""),
        data={"guest_photo_confirmed": "yes"},
    )
    assert response.status_code == 400
    assert app.state.store.load_candidate(created.metadata.case_id) is None


def test_guest_photo_requires_an_image_and_explicit_suitability_confirmation(tmp_path: Path):
    app = create_app(tmp_path)
    client = TestClient(app, follow_redirects=False)
    created = create_case(client, app)
    token = created.metadata.guest_token

    unconfirmed = client.post(
        f"/guest/{token}/capture",
        files=capture_files(),
    )
    assert unconfirmed.status_code == 422

    invalid_image = client.post(
        f"/guest/{token}/capture",
        files={
            **capture_files(),
            "guest_photo": ("guest.jpg", b"not-image", "image/jpeg"),
        },
        data={"guest_photo_confirmed": "yes"},
    )
    assert invalid_image.status_code == 422
    assert app.state.store.load_candidate(created.metadata.case_id) is None


def test_staff_rejects_checkout_that_is_not_later_than_check_in(tmp_path: Path):
    app = create_app(tmp_path)
    client = TestClient(app, follow_redirects=False)

    response = client.post(
        "/staff/cases",
        data={
            "check_in_date": "2026-07-31",
            "check_out_date": "2026-07-31",
            "arrival_time_hotel": "14:25",
            "room": "Sea 04",
            "dummy_profile": "daniel",
        },
    )

    assert response.status_code == 422
    assert app.state.store.list_cases() == []


def test_guest_token_is_single_case_and_expires(tmp_path: Path):
    store = CaseStore(tmp_path)
    first = store.create_case(
        check_in_date=date(2026, 7, 31),
        check_out_date=date(2026, 8, 2),
        arrival_time_hotel=time(14, 25),
        room="One",
        dummy_profile="daniel",
    )
    second = store.create_case(
        check_in_date=date(2026, 7, 31),
        check_out_date=date(2026, 8, 2),
        arrival_time_hotel=time(14, 30),
        room="Two",
        dummy_profile="elena",
    )
    assert store.require_guest_token(first.guest_token).metadata.case_id == first.case_id
    assert store.require_guest_token(first.guest_token).metadata.case_id != second.case_id

    expired = store.create_case(
        check_in_date=date(2026, 7, 31),
        check_out_date=None,
        arrival_time_hotel=time(14, 35),
        room="Three",
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
    assert 'name="arrival_time_hotel"' in dashboard.text
    assert "Defaults to now" in dashboard.text
    assert "Form B reference" not in dashboard.text
    detail = client.get(f"/staff/cases/{created.metadata.case_id}")
    assert detail.status_code == 200
    assert "Government site" in detail.text


def test_mock_portal_reuses_identical_ack_and_rejects_conflicting_duplicate(tmp_path: Path):
    app = create_app(tmp_path)
    client = TestClient(app, follow_redirects=False)
    created = create_case(client, app, profile="aiko")
    values = {name: f"value-{name}" for name in REQUIRED_FORM_C_FIELD_NAMES}

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
