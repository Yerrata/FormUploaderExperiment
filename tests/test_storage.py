from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from formc_app.models import CaseStatus
from formc_app.storage import CaseStore


def test_atomic_status_survives_restart_and_case_cannot_be_claimed_twice(tmp_path: Path):
    store = CaseStore(tmp_path)
    metadata = store.create_case(
        check_in_date=date(2026, 7, 31),
        check_out_date=date(2026, 8, 3),
        room="Sea 04",
        form_b_reference="B-118",
        dummy_profile="daniel",
    )
    store.update_status(metadata.case_id, CaseStatus.READY_FOR_FILING, "Ready")
    claimed = store.claim_ready_case(metadata.case_id)
    assert claimed.status == CaseStatus.FILING
    assert claimed.attempt == 1

    restarted = CaseStore(tmp_path)
    assert restarted.load_state(metadata.case_id).status == CaseStatus.FILING
    with pytest.raises(ValueError):
        restarted.claim_ready_case(metadata.case_id)
    assert not list((tmp_path / "cases" / metadata.case_id).glob("*.tmp"))


def test_cases_are_listed_chronologically_by_check_in_date(tmp_path: Path):
    store = CaseStore(tmp_path)
    later = store.create_case(
        check_in_date=date(2026, 8, 1),
        check_out_date=None,
        room="Later",
        form_b_reference="B-2",
        dummy_profile="aiko",
    )
    earlier = store.create_case(
        check_in_date=date(2026, 7, 30),
        check_out_date=None,
        room="Earlier",
        form_b_reference="B-1",
        dummy_profile="elena",
    )
    assert [case.metadata.case_id for case in store.list_cases()] == [
        earlier.case_id,
        later.case_id,
    ]
