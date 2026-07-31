from __future__ import annotations

from datetime import date
from pathlib import Path
from types import SimpleNamespace

from formc_app.domain import REQUIRED_FIELD_NAMES
from formc_app.dummy_extraction import extract_dummy
from formc_app.models import CandidateField, CandidateFormC, CaseStatus
from formc_app.storage import CaseStore
from formc_app.worker import FilingWorker


def ready_case(store: CaseStore) -> str:
    metadata = store.create_case(
        check_in_date=date(2026, 7, 31),
        check_out_date=date(2026, 8, 3),
        room="Sea 04",
        form_b_reference="B-118",
        dummy_profile="aiko",
    )
    fields = extract_dummy("aiko")
    fields.update(
        {
            "check_in_date": CandidateField(value="2026-07-31", source="staff"),
            "check_out_date": CandidateField(value="2026-08-03", source="staff"),
            "room": CandidateField(value="Sea 04", source="staff"),
            "form_b_reference": CandidateField(value="B-118", source="staff"),
        }
    )
    candidate = CandidateFormC(case_id=metadata.case_id, fields=fields)
    store.save_candidate(candidate)
    store.update_status(metadata.case_id, CaseStatus.READY_FOR_FILING, "Ready")
    return metadata.case_id


class FakeLocator:
    def __init__(self, page, selector: str):
        self.page = page
        self.selector = selector

    def fill(self, value: str):
        field_name = self.selector.split('"')[1]
        self.page.values[field_name] = value

    def click(self):
        self.page.submitted = True

    def get_attribute(self, name: str):
        assert name == "data-acknowledgement"
        return "MOCK-ACK-1001" if self.page.submitted else None


class FakePage:
    def __init__(self):
        self.values = {}
        self.submitted = False

    def goto(self, *_args, **_kwargs):
        return None

    def locator(self, selector: str):
        return FakeLocator(self, selector)

    def screenshot(self, **_kwargs):
        return b"acknowledgement-image" if self.submitted else b"pre-submit-image"

    def wait_for_selector(self, _selector: str):
        return None


class FakeBrowser:
    def __init__(self, page):
        self.page = page

    def new_page(self, **_kwargs):
        return self.page

    def close(self):
        return None


class FakePlaywrightContext:
    def __init__(self, page):
        self.value = SimpleNamespace(
            chromium=SimpleNamespace(launch=lambda **_kwargs: FakeBrowser(page))
        )

    def __enter__(self):
        return self.value

    def __exit__(self, *_args):
        return None


def test_worker_fills_every_field_and_seals_evidence_before_acknowledgement(tmp_path: Path, monkeypatch):
    store = CaseStore(tmp_path)
    case_id = ready_case(store)
    fake_page = FakePage()
    monkeypatch.setattr(
        "formc_app.worker.sync_playwright",
        lambda: FakePlaywrightContext(fake_page),
    )

    FilingWorker(store=store, base_url="http://mock.local").process_case(case_id)

    summary = store.get_summary(case_id)
    assert summary.state.status == CaseStatus.VERIFIED
    assert set(fake_page.values) == set(REQUIRED_FIELD_NAMES)
    assert all(fake_page.values.values())
    assert summary.evidence is not None
    assert summary.evidence.acknowledgement == "MOCK-ACK-1001"
    assert (tmp_path / "cases" / case_id / summary.evidence.screenshot_path).read_bytes() == b"pre-submit-image"
    assert (tmp_path / "cases" / case_id / summary.evidence.acknowledgement_screenshot_path).read_bytes() == b"acknowledgement-image"
    assert not (tmp_path / "cases" / case_id / "worker.lock").exists()
