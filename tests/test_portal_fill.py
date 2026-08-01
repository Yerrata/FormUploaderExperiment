from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from formc_app.fill_plan import (
    FillAction,
    FillOperation,
    FillOptionMatch,
    FillPlanStatus,
    FillValueSource,
    PortalFillPlan,
    _canonical_bytes,
)
from formc_app.models import (
    CandidateField,
    CandidateFormC,
    CaseStatus,
    FilingRequest,
    FillOnlyRunStatus,
    utc_now,
)
from formc_app.portal_catalogue import PortalControl, PortalControlCatalogue, PortalOption
from formc_app.portal_fill import FillOnlyBrowser, PortalFillExecutor, _normalized_label
from formc_app.property_config import YerattaPropertyConfig
from formc_app.storage import CaseStore


def _control(
    ordinal: int,
    name: str,
    *,
    tag: str = "input",
    input_type: str | None = "text",
    choice_value: str | None = None,
    options: list[PortalOption] | None = None,
) -> PortalControl:
    return PortalControl(
        ordinal=ordinal,
        tag=tag,
        name=name,
        element_id=name,
        input_type=input_type,
        choice_value=choice_value,
        options=options or [],
    )


def _executor_case(tmp_path: Path):
    store = CaseStore(tmp_path)
    metadata = store.create_case(
        check_in_date=date(2026, 8, 1),
        check_out_date=date(2026, 8, 2),
        room="Sea 04",
        dummy_profile="daniel",
    )
    candidate = CandidateFormC(
        case_id=metadata.case_id,
        fields={"surname": CandidateField(value="KOH", source="passport_dummy")},
        guest_confirmed_at=utc_now(),
        validated_at=utc_now(),
    )
    store.save_candidate(candidate)
    photo_path = store.save_document(
        metadata.case_id,
        "guest_photo",
        "guest.jpg",
        b"sealed-photo",
    )
    photo_sha256 = store.document_sha256(metadata.case_id, photo_path)
    store.save_filing_request(
        FilingRequest(
            case_id=metadata.case_id,
            request_version=2,
            candidate_sha256=store.candidate_sha256(candidate),
            guest_photo_sha256=photo_sha256,
            guest_photo_source="guest_camera",
            guest_photo_suitability_confirmed_at=utc_now(),
        )
    )
    store.update_status(metadata.case_id, CaseStatus.READY_FOR_FILING, "Ready")

    catalogue = PortalControlCatalogue(
        portal_location="https://indianfrro.gov.in/frro/FormC/formc.jsp",
        control_count=5,
        controls=[
            _control(0, "applicant_surname"),
            _control(
                1,
                "applicant_nationality",
                tag="select",
                input_type=None,
                options=[PortalOption(label="Singapore", value="SGP")],
            ),
            _control(
                2,
                "applicant_next_destination_city_district_IN",
                tag="select",
                input_type=None,
            ),
            _control(
                3,
                "applicant_next_dest_country_flag_r",
                input_type="radio",
                choice_value="I",
            ),
            _control(4, "file1", input_type="file"),
        ],
    )
    (tmp_path / "portal-controls.json").write_text(
        catalogue.model_dump_json(indent=2), encoding="utf-8"
    )
    property_config = YerattaPropertyConfig(
        reference_address="Yeratta test address",
        reference_state_code="1",
        reference_district_code="640",
        reference_pin_code="744211",
    )
    (tmp_path / "property.json").write_text(
        json.dumps(property_config.model_dump(mode="json")), encoding="utf-8"
    )
    plan = PortalFillPlan(
        case_id=metadata.case_id,
        candidate_sha256=store.candidate_sha256(candidate),
        guest_photo_sha256=photo_sha256,
        catalogue_sha256=store.sha256(_canonical_bytes(catalogue)),
        property_config_sha256=store.sha256(_canonical_bytes(property_config)),
        status=FillPlanStatus.READY,
        live_fill_enabled=True,
        operations=[
            FillOperation(
                sequence=1,
                source_field="candidate.surname",
                portal_control="applicant_surname",
                action=FillAction.FILL_TEXT,
                value="KOH",
                value_source=FillValueSource.CANDIDATE,
            ),
            FillOperation(
                sequence=2,
                source_field="candidate.nationality",
                portal_control="applicant_nationality",
                action=FillAction.SELECT_OPTION,
                value="SGP",
                value_source=FillValueSource.CANDIDATE,
            ),
            FillOperation(
                sequence=3,
                source_field="candidate.next_destination_scope",
                portal_control="applicant_next_dest_country_flag_r",
                action=FillAction.CHECK_RADIO,
                value="I",
                value_source=FillValueSource.CANDIDATE,
            ),
            FillOperation(
                sequence=4,
                source_field="candidate.next_destination_city",
                portal_control="applicant_next_destination_city_district_IN",
                action=FillAction.SELECT_OPTION,
                value="South Andaman",
                value_source=FillValueSource.CANDIDATE,
                runtime_option_check_required=True,
                option_match=FillOptionMatch.LABEL,
            ),
            FillOperation(
                sequence=5,
                source_field="filing_request.guest_photo",
                portal_control="file1",
                action=FillAction.UPLOAD_FILE,
                value=photo_path,
                value_source=FillValueSource.FILING_REQUEST,
                value_sha256=photo_sha256,
            ),
        ],
    )
    store.save_fill_plan(metadata.case_id, plan)
    return store, catalogue, plan


class FakeOptionLocator:
    def evaluate_all(self, _script):
        return [
            {"label": "Select", "value": "", "disabled": False},
            {"label": "South Andaman", "value": "640", "disabled": False},
        ]


class FakeLocator:
    def __init__(self, page, selector: str):
        self.page = page
        self.selector = selector

    def count(self):
        return 1

    def locator(self, selector: str):
        assert selector == "option"
        return FakeOptionLocator()

    def fill(self, value: str):
        self.page.actions.append(("fill", self.selector, value))

    def select_option(self, *, value: str):
        self.page.actions.append(("select", self.selector, value))

    def check(self):
        self.page.actions.append(("check", self.selector, None))

    def set_input_files(self, path: str):
        self.page.actions.append(("upload", self.selector, path))


class FakePage:
    url = "https://indianfrro.gov.in/frro/FormC/formc.jsp"

    def __init__(self):
        self.actions: list[tuple[str, str, str | None]] = []

    def locator(self, selector: str):
        return FakeLocator(self, selector)

    def wait_for_timeout(self, _milliseconds: int):
        return None


def test_executor_fills_and_uploads_from_the_sealed_ready_plan(
    tmp_path: Path,
    monkeypatch,
):
    store, catalogue, plan = _executor_case(tmp_path)
    (tmp_path / "portal-controls.json").unlink()
    (tmp_path / "property.json").unlink()
    page = FakePage()
    monkeypatch.setattr("formc_app.portal_fill.is_authenticated_form_c", lambda _page: True)

    result = PortalFillExecutor(store=store, data_root=tmp_path).execute(
        page, plan.case_id
    )

    assert result == plan
    assert [action[0] for action in page.actions] == [
        "fill",
        "select",
        "check",
        "select",
        "upload",
    ]
    assert page.actions[3][2] == "640"
    assert page.actions[4][2] == str(
        store.document_path(plan.case_id, "documents/guest_photo.jpg")
    )
    assert all("pmsbmt" not in action[1] for action in page.actions)


def test_live_option_labels_normalise_case_spacing_and_ampersands():
    assert _normalized_label("Andaman &  Nicobar Islands") == _normalized_label(
        "ANDAMAN AND NICOBAR ISLANDS"
    )


def test_executor_reports_the_exact_operation_the_live_page_rejects(
    tmp_path: Path,
    monkeypatch,
):
    store, _catalogue, plan = _executor_case(tmp_path)
    destination = next(
        operation
        for operation in plan.operations
        if operation.source_field == "candidate.next_destination_city"
    )
    destination.value = "Unknown district"
    store.save_fill_plan(plan.case_id, plan)
    monkeypatch.setattr("formc_app.portal_fill.is_authenticated_form_c", lambda _page: True)

    with pytest.raises(
        ValueError,
        match=(
            "Could not fill candidate.next_destination_city into "
            "applicant_next_destination_city_district_IN"
        ),
    ):
        PortalFillExecutor(
            store=store,
            data_root=tmp_path,
            runtime_option_timeout_ms=0,
        ).execute(FakePage(), plan.case_id)


def test_executor_rejects_a_fill_plan_changed_after_sealing(tmp_path: Path):
    store, _catalogue, plan = _executor_case(tmp_path)
    plan_path = tmp_path / "cases" / plan.case_id / "fill-plan.json"
    plan_path.write_text(plan_path.read_text("utf-8").replace("KOH", "ALTERED"), "utf-8")

    with pytest.raises(ValueError, match="no longer matches its seal"):
        PortalFillExecutor(store=store, data_root=tmp_path).load_verified_plan(
            plan.case_id
        )


def test_fill_only_reuses_the_existing_authenticated_window(
    tmp_path: Path,
    monkeypatch,
):
    page = FakePage()
    browser_context = SimpleNamespace(pages=[page])
    connected_browser = SimpleNamespace(contexts=[browser_context])
    connection_urls = []

    class FakePlaywright:
        chromium = SimpleNamespace(
            connect_over_cdp=lambda url: (
                connection_urls.append(url) or connected_browser
            )
        )

    class FakePlaywrightContext:
        def __enter__(self):
            return FakePlaywright()

        def __exit__(self, *_args):
            return None

    executed = []
    plan = SimpleNamespace(operations=[1, 2, 3])
    executor = SimpleNamespace(
        data_root=tmp_path,
        execute=lambda selected_page, case_id: (
            executed.append((selected_page, case_id)) or plan
        ),
    )
    progress = []
    monkeypatch.setattr(
        "formc_app.portal_fill.sync_playwright",
        lambda: FakePlaywrightContext(),
    )
    monkeypatch.setattr(
        "formc_app.portal_fill.is_authenticated_form_c",
        lambda selected_page: selected_page is page,
    )

    result = FillOnlyBrowser(executor=executor).run(
        "YRT-TEST",
        hold_for_review=False,
        wait_for_browser_close=False,
        progress=lambda status, message, count: progress.append(
            (status, message, count)
        ),
    )

    assert result is plan
    assert connection_urls == ["http://127.0.0.1:9222"]
    assert executed == [(page, "YRT-TEST")]
    assert [item[0] for item in progress] == [
        FillOnlyRunStatus.STARTING,
        FillOnlyRunStatus.FILLING,
        FillOnlyRunStatus.REVIEW,
    ]
