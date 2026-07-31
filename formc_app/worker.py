from __future__ import annotations

import argparse
import hashlib
import os
import time
from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import sync_playwright

from formc_app.domain import REQUIRED_FIELD_NAMES
from formc_app.models import CaseStatus, EvidenceManifest, utc_now
from formc_app.storage import CaseStore


@dataclass
class FilingWorker:
    store: CaseStore
    base_url: str
    headless: bool = True

    def process_case(self, case_id: str) -> None:
        os.environ.setdefault(
            "PLAYWRIGHT_BROWSERS_PATH",
            str(Path(".playwright-browsers").resolve()),
        )
        state = self.store.claim_ready_case(case_id)
        submitted = False
        try:
            candidate = self.store.load_candidate(case_id)
            if candidate is None:
                raise ValueError("Candidate Form C is missing")
            missing = candidate.missing(REQUIRED_FIELD_NAMES)
            if missing:
                raise ValueError(f"Candidate Form C is incomplete: {', '.join(missing)}")

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=self.headless)
                page = browser.new_page(viewport={"width": 1200, "height": 900})
                page.goto(
                    f"{self.base_url}/mock-government/form-c/{case_id}",
                    wait_until="networkidle",
                )
                for field_name in REQUIRED_FIELD_NAMES:
                    page.locator(f'[name="{field_name}"]').fill(candidate.value(field_name) or "")

                candidate_bytes = self.store.canonical_candidate_bytes(candidate)
                screenshot_bytes = page.screenshot(full_page=True)
                screenshot_path = self.store.save_evidence_file(
                    case_id,
                    f"pre-submit-attempt-{state.attempt}.png",
                    screenshot_bytes,
                )
                candidate_hash = hashlib.sha256(candidate_bytes).hexdigest()
                screenshot_hash = hashlib.sha256(screenshot_bytes).hexdigest()
                combined_hash = hashlib.sha256(candidate_bytes + b"\n" + screenshot_bytes).hexdigest()
                evidence = EvidenceManifest(
                    case_id=case_id,
                    attempt=state.attempt,
                    captured_at=utc_now(),
                    candidate_sha256=candidate_hash,
                    screenshot_sha256=screenshot_hash,
                    combined_sha256=combined_hash,
                    screenshot_path=screenshot_path,
                )
                self.store.save_evidence(evidence)
                self.store.update_status(
                    case_id,
                    CaseStatus.PRE_SUBMIT_EVIDENCE_SEALED,
                    "Mock Form C filled and pre-submit evidence sealed",
                )

                page.locator('button[type="submit"]').click()
                page.wait_for_selector("[data-acknowledgement]")
                acknowledgement = page.locator("[data-acknowledgement]").get_attribute(
                    "data-acknowledgement"
                )
                if not acknowledgement:
                    submitted = True
                    raise RuntimeError("Mock portal submitted without a readable acknowledgement")
                submitted = True
                acknowledgement_screenshot = page.screenshot(full_page=True)
                acknowledgement_path = self.store.save_evidence_file(
                    case_id,
                    f"acknowledgement-attempt-{state.attempt}.png",
                    acknowledgement_screenshot,
                )
                evidence.acknowledgement = acknowledgement
                evidence.submitted_at = utc_now()
                evidence.acknowledgement_screenshot_path = acknowledgement_path
                self.store.save_evidence(evidence)
                self.store.update_status(
                    case_id,
                    CaseStatus.VERIFIED,
                    f"Mock acknowledgement {acknowledgement} captured",
                )
                browser.close()
        except Exception as exc:
            if submitted:
                self.store.update_status(
                    case_id,
                    CaseStatus.SUBMITTED_UNVERIFIED,
                    f"Submission outcome requires reconciliation: {exc}",
                )
            else:
                self.store.update_status(
                    case_id,
                    CaseStatus.BLOCKED,
                    f"Worker stopped safely: {exc}",
                )
            raise
        finally:
            self.store.release_claim(case_id)

    def process_ready(self) -> int:
        processed = 0
        for case_id in self.store.ready_case_ids():
            try:
                self.process_case(case_id)
            except Exception:
                pass
            processed += 1
        return processed


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local Yeratta Filing Worker")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--interval", type=float, default=2.0)
    args = parser.parse_args()
    worker = FilingWorker(
        store=CaseStore(args.data_dir),
        base_url=args.base_url.rstrip("/"),
        headless=not args.headed,
    )
    if not args.watch:
        worker.process_ready()
        return
    while True:
        worker.process_ready()
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
