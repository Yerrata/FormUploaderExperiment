from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock, Thread
from typing import Callable

from formc_app.models import FillOnlyRunState, FillOnlyRunStatus, utc_now
from formc_app.portal_fill import FillOnlyBrowser, PortalFillExecutor
from formc_app.portal_session import DEFAULT_PORTAL_URL
from formc_app.storage import CaseStore


ACTIVE_FILL_STATUSES = {
    FillOnlyRunStatus.STARTING,
    FillOnlyRunStatus.WAITING_FOR_LOGIN,
    FillOnlyRunStatus.FILLING,
    FillOnlyRunStatus.REVIEW,
}


def _safe_error_message(error: Exception) -> str:
    message = str(error).splitlines()[0].strip() or error.__class__.__name__
    message = re.sub(r"https?://\S+", "[government portal]", message)
    return message[:500]


@dataclass
class StaffFilingCoordinator:
    store: CaseStore
    data_root: Path
    portal_url: str = DEFAULT_PORTAL_URL
    authentication_timeout_seconds: float = 600
    browser_factory: Callable[[PortalFillExecutor], FillOnlyBrowser] | None = None
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)
    _active_case_id: str | None = field(default=None, init=False)

    def is_active(self, case_id: str | None = None) -> bool:
        with self._lock:
            return self._active_case_id is not None and (
                case_id is None or self._active_case_id == case_id
            )

    def require_idle(self) -> None:
        with self._lock:
            if self._active_case_id is not None:
                raise ValueError(
                    f"Fill-only is already open for {self._active_case_id}; close that Chromium window first"
                )

    def display_state(self, case_id: str) -> FillOnlyRunState:
        state = self.store.load_fill_only_run(case_id)
        if state.status in ACTIVE_FILL_STATUSES and not self.is_active(case_id):
            state.status = FillOnlyRunStatus.FAILED
            state.message = (
                "The previous fill-only run ended when the staff app stopped. "
                "No automated submission occurred; run it again safely."
            )
            state.updated_at = utc_now()
            state.finished_at = state.updated_at
            self.store.save_fill_only_run(state)
        return state

    def launch(self, case_id: str) -> None:
        executor = PortalFillExecutor(store=self.store, data_root=self.data_root)
        # Verify only the sealed execution contract before opening the browser.
        executor.load_verified_plan(case_id)
        with self._lock:
            if self._active_case_id is not None:
                raise ValueError(
                    f"Fill-only is already open for {self._active_case_id}; close that Chromium window first"
                )
            self._active_case_id = case_id
            started_at = utc_now()
            self.store.save_fill_only_run(
                FillOnlyRunState(
                    case_id=case_id,
                    status=FillOnlyRunStatus.STARTING,
                    message="Opening the dedicated government-portal Chromium window",
                    started_at=started_at,
                    updated_at=started_at,
                )
            )
        Thread(
            target=self._run,
            args=(case_id, executor),
            name=f"formc-fill-only-{case_id}",
            daemon=True,
        ).start()

    def _run(self, case_id: str, executor: PortalFillExecutor) -> None:
        def progress(
            status: FillOnlyRunStatus,
            message: str,
            operations_filled: int | None,
        ) -> None:
            previous = self.store.load_fill_only_run(case_id)
            now = utc_now()
            self.store.save_fill_only_run(
                FillOnlyRunState(
                    case_id=case_id,
                    status=status,
                    message=message,
                    updated_at=now,
                    started_at=previous.started_at or now,
                    finished_at=now
                    if status in {FillOnlyRunStatus.CLOSED, FillOnlyRunStatus.FAILED}
                    else None,
                    operations_filled=operations_filled
                    if operations_filled is not None
                    else previous.operations_filled,
                )
            )

        try:
            browser = (
                self.browser_factory(executor)
                if self.browser_factory is not None
                else FillOnlyBrowser(
                    executor=executor,
                    portal_url=self.portal_url,
                    authentication_timeout_seconds=self.authentication_timeout_seconds,
                )
            )
            plan = browser.run(
                case_id,
                hold_for_review=False,
                wait_for_browser_close=True,
                progress=progress,
            )
            state = self.store.load_fill_only_run(case_id)
            if state.status != FillOnlyRunStatus.CLOSED:
                progress(
                    FillOnlyRunStatus.CLOSED,
                    "Chromium closed without an automated submission; fill-only can be run again",
                    len(plan.operations),
                )
        except Exception as error:
            previous = self.store.load_fill_only_run(case_id)
            now = utc_now()
            self.store.save_fill_only_run(
                FillOnlyRunState(
                    case_id=case_id,
                    status=FillOnlyRunStatus.FAILED,
                    message=(
                        f"Fill-only stopped safely: {_safe_error_message(error)}. "
                        "No automated submission occurred; correct the problem and retry."
                    ),
                    updated_at=now,
                    started_at=previous.started_at,
                    finished_at=now,
                    operations_filled=previous.operations_filled,
                )
            )
        finally:
            with self._lock:
                if self._active_case_id == case_id:
                    self._active_case_id = None

    def wait_until_idle(self, timeout_seconds: float = 2) -> bool:
        deadline = time.monotonic() + timeout_seconds
        while self.is_active() and time.monotonic() < deadline:
            time.sleep(0.01)
        return not self.is_active()
