from __future__ import annotations

from datetime import date
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

import formc_app.main as main_module
from formc_app.fill_plan import FillPlanStatus, PortalFillPlan
from formc_app.main import create_app
from formc_app.models import CaseStatus, FillOnlyRunState, FillOnlyRunStatus
from formc_app.staff_filing import StaffFilingCoordinator
from formc_app.storage import CaseStore


def _ready_case(store: CaseStore) -> str:
    metadata = store.create_case(
        check_in_date=date(2026, 8, 1),
        check_out_date=date(2026, 8, 3),
        room="Sea 04",
        dummy_profile="daniel",
    )
    store.update_status(
        metadata.case_id,
        CaseStatus.READY_FOR_FILING,
        "Guest confirmed one Filing Request; ready to fill",
    )
    return metadata.case_id


def _plan(case_id: str) -> PortalFillPlan:
    return PortalFillPlan(
        case_id=case_id,
        candidate_sha256="a" * 64,
        guest_photo_sha256="b" * 64,
        catalogue_sha256="c" * 64,
        property_config_sha256="d" * 64,
        status=FillPlanStatus.READY,
        live_fill_enabled=True,
    )


def test_staff_case_offers_direct_fill_without_a_preflight_gate(tmp_path: Path):
    app = create_app(tmp_path)
    case_id = _ready_case(app.state.store)
    client = TestClient(app, follow_redirects=False)

    first_page = client.get(f"/staff/cases/{case_id}")
    assert first_page.status_code == 200
    assert "Fill Form C in portal window" in first_page.text
    assert "one reusable Chromium window" in first_page.text
    assert "preflight" not in first_page.text.casefold()
    assert "Run mock filing worker" not in first_page.text
    assert "mock-government.local" not in first_page.text


def test_staff_fill_action_launches_the_coordinator_without_a_cli(
    tmp_path: Path,
    monkeypatch,
):
    app = create_app(tmp_path)
    case_id = _ready_case(app.state.store)
    prepared: list[str] = []
    launched: list[str] = []

    def fake_prepare(*, store, data_root, case_id):
        assert data_root == tmp_path
        prepared.append(case_id)
        plan = _plan(case_id)
        store.save_fill_plan(case_id, plan)
        return plan

    def fake_launch(selected_case_id: str) -> None:
        launched.append(selected_case_id)
        app.state.store.save_fill_only_run(
            FillOnlyRunState(
                case_id=selected_case_id,
                status=FillOnlyRunStatus.REVIEW,
                message="Form filled without submission",
                operations_filled=38,
            )
        )

    monkeypatch.setattr(main_module, "prepare_fill_plan", fake_prepare)
    monkeypatch.setattr(app.state.staff_filing, "launch", fake_launch)
    client = TestClient(app, follow_redirects=False)
    response = client.post(f"/staff/cases/{case_id}/fill-only")

    assert response.status_code == 303
    assert prepared == [case_id]
    assert launched == [case_id]
    run = app.state.store.load_fill_only_run(case_id)
    assert run.status == FillOnlyRunStatus.REVIEW
    assert run.operations_filled == 38


class _SuccessfulBrowser:
    def run(self, case_id, *, hold_for_review, wait_for_browser_close, progress):
        assert hold_for_review is False
        assert wait_for_browser_close is False
        progress(
            FillOnlyRunStatus.WAITING_FOR_LOGIN,
            "Complete login and CAPTCHA",
            None,
        )
        progress(FillOnlyRunStatus.FILLING, "Filling", None)
        progress(FillOnlyRunStatus.REVIEW, "Review", 3)
        return SimpleNamespace(operations=[1, 2, 3])


class _FailingBrowser:
    def run(self, case_id, *, hold_for_review, wait_for_browser_close, progress):
        progress(FillOnlyRunStatus.FILLING, "Filling", None)
        raise ValueError("Could not fill candidate.sex into applicant_sex")


def test_coordinator_records_completion_and_safe_partial_fill_failure(
    tmp_path: Path,
    monkeypatch,
):
    store = CaseStore(tmp_path)
    case_id = _ready_case(store)
    monkeypatch.setattr(
        "formc_app.staff_filing.PortalFillExecutor.load_verified_plan",
        lambda self, selected_case_id: SimpleNamespace(),
    )
    coordinator = StaffFilingCoordinator(
        store=store,
        data_root=tmp_path,
        browser_factory=lambda _executor: _SuccessfulBrowser(),
    )

    coordinator.launch(case_id)
    assert coordinator.wait_until_idle()
    completed = store.load_fill_only_run(case_id)
    assert completed.status == FillOnlyRunStatus.REVIEW
    assert completed.operations_filled == 3
    assert completed.finished_at is not None
    assert store.load_state(case_id).status == CaseStatus.READY_FOR_FILING

    coordinator.browser_factory = lambda _executor: _FailingBrowser()
    coordinator.launch(case_id)
    assert coordinator.wait_until_idle()
    failed = store.load_fill_only_run(case_id)
    assert failed.status == FillOnlyRunStatus.FAILED
    assert "Could not fill candidate.sex into applicant_sex" in failed.message
    assert "No automated submission occurred" in failed.message
    assert store.load_state(case_id).status == CaseStatus.READY_FOR_FILING


def test_coordinator_rejects_an_invalid_plan_before_starting_a_browser(
    tmp_path: Path,
    monkeypatch,
):
    store = CaseStore(tmp_path)
    case_id = _ready_case(store)
    monkeypatch.setattr(
        "formc_app.staff_filing.PortalFillExecutor.load_verified_plan",
        lambda self, selected_case_id: (_ for _ in ()).throw(
            ValueError("The fill plan no longer matches its seal")
        ),
    )
    browser_started = False

    def browser_factory(_executor):
        nonlocal browser_started
        browser_started = True
        return _SuccessfulBrowser()

    coordinator = StaffFilingCoordinator(
        store=store,
        data_root=tmp_path,
        browser_factory=browser_factory,
    )

    try:
        coordinator.launch(case_id)
    except ValueError as error:
        assert "no longer matches its seal" in str(error)
    else:
        raise AssertionError("A tampered fill plan must be rejected")

    assert browser_started is False
    assert coordinator.is_active() is False
