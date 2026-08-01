from __future__ import annotations

import argparse
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import Locator, Page, sync_playwright

from formc_app.fill_plan import (
    CATALOGUE_FILENAME,
    FillAction,
    FillOptionMatch,
    FillPlanStatus,
    PortalFillPlan,
    _canonical_bytes,
    compile_fill_plan,
)
from formc_app.models import CaseStatus
from formc_app.portal_catalogue import PortalControl, PortalControlCatalogue, catalogue_page_controls
from formc_app.portal_mapping import LIVE_SUBMISSION_CONTROL_IDS
from formc_app.portal_session import DEFAULT_PORTAL_URL, is_authenticated_form_c, validate_portal_url
from formc_app.property_config import load_property_config
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
    return " ".join(value.split()).casefold()


@dataclass
class PortalFillExecutor:
    store: CaseStore
    data_root: Path
    runtime_option_timeout_ms: int = 10_000

    def _load_catalogue(self) -> PortalControlCatalogue:
        path = self.data_root / CATALOGUE_FILENAME
        try:
            return PortalControlCatalogue.model_validate_json(path.read_text("utf-8"))
        except FileNotFoundError as exc:
            raise ValueError(f"Safe portal catalogue is missing: {path}") from exc

    def load_verified_plan(self, case_id: str) -> tuple[PortalFillPlan, PortalControlCatalogue]:
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
            raise ValueError("Only an unblocked READY fill-only plan may be executed")
        if [operation.sequence for operation in plan.operations] != list(
            range(1, len(plan.operations) + 1)
        ):
            raise ValueError("Fill-plan operations are not a contiguous ordered sequence")
        if any(
            operation.portal_control in LIVE_SUBMISSION_CONTROL_IDS
            for operation in plan.operations
        ):
            raise ValueError("Fill plan targets a forbidden submission control")

        summary = self.store.get_summary(case_id)
        if summary.state.status != CaseStatus.READY_FOR_FILING:
            raise ValueError(f"Case is not ready for fill-only: {summary.state.status}")
        candidate = summary.candidate
        if candidate is None:
            raise ValueError("Candidate Form C is missing")
        if candidate.guest_confirmed_at is None or candidate.validated_at is None:
            raise ValueError("Candidate is no longer guest-confirmed and validated")
        candidate_sha256 = self.store.candidate_sha256(candidate)
        if candidate_sha256 != plan.candidate_sha256:
            raise ValueError("Candidate no longer matches the sealed fill plan")
        filing_request = self.store.load_filing_request(case_id)
        if filing_request is None or filing_request.candidate_sha256 != candidate_sha256:
            raise ValueError("Filing Request no longer matches the sealed Candidate")

        catalogue = self._load_catalogue()
        if self.store.sha256(_canonical_bytes(catalogue)) != plan.catalogue_sha256:
            raise ValueError("Portal catalogue no longer matches the sealed fill plan")
        property_config = load_property_config(self.data_root)
        if self.store.sha256(_canonical_bytes(property_config)) != plan.property_config_sha256:
            raise ValueError("Property configuration no longer matches the sealed fill plan")

        photo_path = summary.metadata.guest_photo_document
        if photo_path is None:
            raise ValueError("The sealed guest photograph is missing")
        photo_sha256 = self.store.document_sha256(case_id, photo_path)
        expected_plan = compile_fill_plan(
            candidate=candidate,
            catalogue=catalogue,
            property_config=property_config,
            candidate_sha256=candidate_sha256,
            guest_photo_path=photo_path,
            guest_photo_sha256=photo_sha256,
        )
        if expected_plan != plan:
            raise ValueError("Fill plan is not the deterministic plan for its sealed inputs")

        upload_operations = [
            operation
            for operation in plan.operations
            if operation.action == FillAction.UPLOAD_FILE
        ]
        if len(upload_operations) != 1:
            raise ValueError("A supported fill plan must contain exactly one photograph upload")
        upload = upload_operations[0]
        if (
            upload.value != photo_path
            or not upload.value_sha256
            or photo_sha256 != upload.value_sha256
            or photo_sha256 != plan.guest_photo_sha256
            or photo_sha256 != filing_request.guest_photo_sha256
        ):
            raise ValueError("Guest photograph no longer matches the sealed fill plan")
        return plan, catalogue

    @staticmethod
    def _catalogue_controls(
        catalogue: PortalControlCatalogue,
        identifier: str,
    ) -> list[PortalControl]:
        return [
            control
            for control in catalogue.controls
            if control.name == identifier or control.element_id == identifier
        ]

    @staticmethod
    def _selector(control: PortalControl, identifier: str) -> str:
        if SAFE_IDENTIFIER.fullmatch(identifier) is None:
            raise ValueError(f"Unsafe portal control identifier: {identifier!r}")
        if control.name == identifier:
            return f'[name="{identifier}"]'
        if control.element_id == identifier:
            return f"#{identifier}"
        raise ValueError(f"Catalogue does not identify portal control {identifier}")

    def _single_locator(
        self,
        page: Page,
        catalogue: PortalControlCatalogue,
        identifier: str,
    ) -> tuple[PortalControl, Locator]:
        controls = self._catalogue_controls(catalogue, identifier)
        if len(controls) != 1:
            raise ValueError(
                f"Expected exactly one catalogued control named {identifier}; found {len(controls)}"
            )
        control = controls[0]
        locator = page.locator(self._selector(control, identifier))
        if locator.count() != 1:
            raise ValueError(f"Live portal control {identifier} no longer matches the catalogue")
        return control, locator

    def _radio_locator(
        self,
        page: Page,
        catalogue: PortalControlCatalogue,
        identifier: str,
        value: str,
    ) -> Locator:
        matches = [
            control
            for control in self._catalogue_controls(catalogue, identifier)
            if control.tag == "input"
            and control.input_type == "radio"
            and control.choice_value == value
            and not control.disabled
            and not control.read_only
        ]
        if len(matches) != 1 or SAFE_IDENTIFIER.fullmatch(identifier) is None:
            raise ValueError(f"Live radio choice {identifier}={value!r} is not uniquely safe")
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
        plan, catalogue = self.load_verified_plan(case_id)
        if not is_authenticated_form_c(page):
            raise ValueError("Authenticated Form C controls were not found")
        live_controls = catalogue_page_controls(page)
        if [control.model_dump(mode="json") for control in live_controls] != [
            control.model_dump(mode="json") for control in catalogue.controls
        ]:
            raise ValueError("Live Form C controls have drifted from the sealed catalogue")

        for operation in plan.operations:
            if operation.action == FillAction.CHECK_RADIO:
                self._radio_locator(
                    page,
                    catalogue,
                    operation.portal_control,
                    operation.value,
                ).check()
                continue

            control, locator = self._single_locator(
                page,
                catalogue,
                operation.portal_control,
            )
            if operation.action == FillAction.FILL_TEXT:
                if control.tag not in {"input", "textarea"}:
                    raise ValueError(f"Control {operation.portal_control} is not text-capable")
                locator.fill(operation.value)
            elif operation.action == FillAction.SELECT_OPTION:
                if control.tag != "select":
                    raise ValueError(f"Control {operation.portal_control} is not a select")
                value = (
                    self._runtime_option_value(page, locator, operation)
                    if operation.runtime_option_check_required
                    else operation.value
                )
                locator.select_option(value=value)
            elif operation.action == FillAction.UPLOAD_FILE:
                if control.tag != "input" or control.input_type != "file":
                    raise ValueError(f"Control {operation.portal_control} is not a file input")
                locator.set_input_files(str(self.store.document_path(case_id, operation.value)))
            else:
                raise ValueError(f"Unsupported fill-only action: {operation.action}")
        return plan


@dataclass
class FillOnlyBrowser:
    executor: PortalFillExecutor
    portal_url: str = DEFAULT_PORTAL_URL
    authentication_timeout_seconds: float = 600

    @property
    def profile_dir(self) -> Path:
        return self.executor.data_root / "portal-browser-profile"

    def run(self, case_id: str, *, hold_for_review: bool = True) -> PortalFillPlan:
        validate_portal_url(self.portal_url)
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault(
            "PLAYWRIGHT_BROWSERS_PATH",
            str(Path(".playwright-browsers").resolve()),
        )
        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir),
                headless=False,
                viewport=None,
            )
            try:
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(self.portal_url, wait_until="domcontentloaded")
                deadline = time.monotonic() + self.authentication_timeout_seconds
                while not is_authenticated_form_c(page):
                    if time.monotonic() >= deadline:
                        raise ValueError(
                            "Authenticated Form C controls were not found; complete normal login and CAPTCHA"
                        )
                    page.wait_for_timeout(500)
                plan = self.executor.execute(page, case_id)
                if hold_for_review:
                    try:
                        input(
                            "Form filled. Review it in Chromium. Press Enter to close without submitting. "
                        )
                    except EOFError:
                        pass
                return plan
            finally:
                context.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fill one authenticated Form C from a sealed READY plan without submitting"
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
    print(f"Filled {len(plan.operations)} controls from sealed READY plan {plan.case_id}.")
    print("No submission control was clicked.")


if __name__ == "__main__":
    main()
