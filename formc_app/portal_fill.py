from __future__ import annotations

import argparse
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Locator, Page, sync_playwright

from formc_app.fill_plan import (
    FillAction,
    FillOptionMatch,
    FillPlanStatus,
    PortalFillPlan,
)
from formc_app.models import FillOnlyRunStatus
from formc_app.portal_mapping import LIVE_SUBMISSION_CONTROL_IDS
from formc_app.portal_session import (
    DEFAULT_PORTAL_URL,
    PORTAL_CDP_URL,
    is_authenticated_form_c,
    validate_portal_url,
)
from formc_app.storage import CaseStore


SAFE_IDENTIFIER = re.compile(r"[A-Za-z0-9_:-]+")
OPTION_SCRIPT = r"""
(options) => options.map((option) => ({
  label: String(option.textContent || "").replace(/\s+/g, " ").trim(),
  value: String(option.value),
  disabled: Boolean(option.disabled)
}))
"""


def _normalized_label(value: str) -> str:
    words = re.sub(r"[^a-z0-9]+", " ", value.replace("&", " and ").casefold())
    return " ".join(words.split())


@dataclass
class PortalFillExecutor:
    store: CaseStore
    data_root: Path
    runtime_option_timeout_ms: int = 10_000

    def load_verified_plan(self, case_id: str) -> PortalFillPlan:
        plan = PortalFillPlan.model_validate_json(
            self.store.load_sealed_fill_plan_bytes(case_id)
        )
        if plan.case_id != case_id:
            raise ValueError("Fill plan case ID does not match its case folder")
        if (
            plan.status != FillPlanStatus.READY
            or not plan.live_fill_enabled
            or plan.live_submit_enabled
            or plan.blockers
        ):
            raise ValueError("The sealed plan is not executable under the no-submit rules")
        if [operation.sequence for operation in plan.operations] != list(
            range(1, len(plan.operations) + 1)
        ):
            raise ValueError("Fill-plan operations are not a contiguous ordered sequence")
        if any(
            operation.portal_control in LIVE_SUBMISSION_CONTROL_IDS
            for operation in plan.operations
        ):
            raise ValueError("Fill plan targets a forbidden submission control")

        return plan

    @staticmethod
    def _selector(identifier: str) -> str:
        if SAFE_IDENTIFIER.fullmatch(identifier) is None:
            raise ValueError(f"Unsafe portal control identifier: {identifier!r}")
        return f'[name="{identifier}"], #{identifier}'

    def _single_locator(
        self,
        page: Page,
        identifier: str,
    ) -> Locator:
        locator = page.locator(self._selector(identifier))
        if locator.count() != 1:
            raise ValueError(f"Live portal control {identifier} was not found exactly once")
        return locator

    def _radio_locator(
        self,
        page: Page,
        identifier: str,
        value: str,
    ) -> Locator:
        if SAFE_IDENTIFIER.fullmatch(identifier) is None:
            raise ValueError(f"Unsafe portal control identifier: {identifier!r}")
        if SAFE_IDENTIFIER.fullmatch(value) is None:
            raise ValueError(f"Unsafe portal radio value: {value!r}")
        locator = page.locator(f'[name="{identifier}"][value="{value}"]')
        if locator.count() != 1:
            raise ValueError(f"Live radio choice {identifier}={value!r} is missing")
        return locator

    def _runtime_option_value(self, page: Page, locator: Locator, operation) -> str:
        deadline = time.monotonic() + self.runtime_option_timeout_ms / 1000
        while True:
            options = locator.locator("option").evaluate_all(OPTION_SCRIPT)
            if operation.option_match == FillOptionMatch.VALUE:
                matches = [
                    option
                    for option in options
                    if option["value"] == operation.value and not option["disabled"]
                ]
            else:
                expected = _normalized_label(operation.value)
                matches = [
                    option
                    for option in options
                    if _normalized_label(option["label"]) == expected
                    and option["value"]
                    and not option["disabled"]
                ]
            if len(matches) == 1:
                return str(matches[0]["value"])
            if len(matches) > 1:
                raise ValueError(
                    f"Live control {operation.portal_control} has ambiguous matching options"
                )
            if time.monotonic() >= deadline:
                raise ValueError(
                    f"Live control {operation.portal_control} did not expose the sealed option"
                )
            page.wait_for_timeout(100)

    def execute(self, page: Page, case_id: str) -> PortalFillPlan:
        plan = self.load_verified_plan(case_id)
        if not is_authenticated_form_c(page):
            raise ValueError("Authenticated Form C controls were not found")

        for operation in plan.operations:
            try:
                if operation.action == FillAction.CHECK_RADIO:
                    self._radio_locator(
                        page,
                        operation.portal_control,
                        operation.value,
                    ).check()
                    continue

                locator = self._single_locator(page, operation.portal_control)
                if operation.action == FillAction.FILL_TEXT:
                    locator.fill(operation.value)
                elif operation.action == FillAction.SELECT_OPTION:
                    value = (
                        self._runtime_option_value(page, locator, operation)
                        if operation.runtime_option_check_required
                        else operation.value
                    )
                    locator.select_option(value=value)
                elif operation.action == FillAction.UPLOAD_FILE:
                    locator.set_input_files(
                        str(self.store.document_path(case_id, operation.value))
                    )
                else:
                    raise ValueError(f"Unsupported fill-only action: {operation.action}")
            except (PlaywrightError, ValueError) as error:
                raise ValueError(
                    f"Could not fill {operation.source_field} into "
                    f"{operation.portal_control}: {error}"
                ) from error
        return plan


@dataclass
class FillOnlyBrowser:
    executor: PortalFillExecutor
    portal_url: str = DEFAULT_PORTAL_URL
    cdp_url: str = PORTAL_CDP_URL
    authentication_timeout_seconds: float = 600

    def run(
        self,
        case_id: str,
        *,
        hold_for_review: bool = True,
        wait_for_browser_close: bool = False,
        progress: Callable[[FillOnlyRunStatus, str, int | None], None] | None = None,
    ) -> PortalFillPlan:
        def report(
            status: FillOnlyRunStatus,
            message: str,
            operations_filled: int | None = None,
        ) -> None:
            if progress is not None:
                progress(status, message, operations_filled)

        validate_portal_url(self.portal_url)
        os.environ.setdefault(
            "PLAYWRIGHT_BROWSERS_PATH",
            str(Path(".playwright-browsers").resolve()),
        )
        report(
            FillOnlyRunStatus.STARTING,
            "Connecting to the existing government-portal Chromium window",
        )
        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.connect_over_cdp(self.cdp_url)
            except PlaywrightError as error:
                raise ValueError(
                    "The reusable portal window is not open; run formc-portal-login "
                    "once and keep its Chromium window open"
                ) from error
            contexts = browser.contexts
            if len(contexts) != 1 or not contexts[0].pages:
                raise ValueError("The reusable portal window has no active page")
            context = contexts[0]
            authenticated_pages = [
                candidate
                for candidate in context.pages
                if is_authenticated_form_c(candidate)
            ]
            page = authenticated_pages[0] if authenticated_pages else context.pages[0]
            if not authenticated_pages:
                page.goto(self.portal_url, wait_until="domcontentloaded")
            try:
                deadline = time.monotonic() + self.authentication_timeout_seconds
                if not is_authenticated_form_c(page):
                    report(
                        FillOnlyRunStatus.WAITING_FOR_LOGIN,
                        "Complete the normal government login and CAPTCHA in the existing Chromium window",
                    )
                while not is_authenticated_form_c(page):
                    if time.monotonic() >= deadline:
                        raise ValueError(
                            "Authenticated Form C controls were not found; complete normal login and CAPTCHA"
                        )
                    page.wait_for_timeout(500)
                report(
                    FillOnlyRunStatus.FILLING,
                    "Authenticated Form C found; filling the sealed plan in order",
                )
                plan = self.executor.execute(page, case_id)
                report(
                    FillOnlyRunStatus.REVIEW,
                    "Form filled without submission. Review it in the reusable Chromium window",
                    len(plan.operations),
                )
                return plan
            except PlaywrightError as error:
                raise ValueError("The reusable portal window closed during fill-only") from error


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fill one authenticated Form C directly from a sealed plan without submitting"
    )
    parser.add_argument("case_id")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument(
        "--portal-url",
        default=os.environ.get("FORMC_PORTAL_URL", DEFAULT_PORTAL_URL),
    )
    parser.add_argument("--timeout", type=float, default=600)
    args = parser.parse_args()

    print("Fill-only mode: submission controls will never be clicked.")
    print("Complete the normal government login and CAPTCHA if prompted.")
    try:
        plan = FillOnlyBrowser(
            executor=PortalFillExecutor(
                store=CaseStore(args.data_dir),
                data_root=args.data_dir,
            ),
            portal_url=args.portal_url,
            authentication_timeout_seconds=args.timeout,
        ).run(args.case_id)
    except (LookupError, OSError, RuntimeError, ValueError) as error:
        print(f"Fill-only stopped safely: {error}")
        raise SystemExit(1) from None
    print(f"Filled {len(plan.operations)} controls from sealed plan {plan.case_id}.")
    print("No submission control was clicked.")


if __name__ == "__main__":
    main()
