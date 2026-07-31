from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from playwright.sync_api import Page, sync_playwright
from pydantic import BaseModel, Field

from formc_app.models import utc_now
from formc_app.storage import CaseStore


DEFAULT_PORTAL_URL = "https://indianfrro.gov.in/frro/FormC"
PORTAL_HOST = "indianfrro.gov.in"
PORTAL_PATH_PREFIX = "/frro/FormC"


class PortalSessionState(StrEnum):
    READY = "READY"
    NEEDS_LOGIN = "NEEDS_LOGIN"


class PortalSessionSnapshot(BaseModel):
    state: PortalSessionState
    checked_at: datetime = Field(default_factory=utc_now)
    portal_location: str
    message: str


def safe_portal_location(url: str) -> str:
    """Retain the portal location without persisting query tokens or fragments."""
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def validate_portal_url(url: str) -> None:
    """Refuse to open the credential-bearing profile on an unofficial URL."""
    parsed = urlsplit(url)
    valid_path = parsed.path == PORTAL_PATH_PREFIX or parsed.path.startswith(
        f"{PORTAL_PATH_PREFIX}/"
    )
    if (
        parsed.scheme != "https"
        or parsed.hostname != PORTAL_HOST
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in {None, 443}
        or not valid_path
    ):
        raise ValueError("Portal URL must be the official HTTPS Form C portal")


def is_authenticated_form_c(page: Page) -> bool:
    """Return true only when a plausible authenticated Form C form is visible."""
    parsed = urlsplit(page.url)
    if parsed.scheme != "https" or parsed.hostname != PORTAL_HOST:
        return False
    if parsed.path != PORTAL_PATH_PREFIX and not parsed.path.startswith(
        f"{PORTAL_PATH_PREFIX}/"
    ):
        return False

    try:
        credential_controls = page.locator(
            'input[type="password"], input[name*="captcha" i], img[src*="captcha" i]'
        ).count()
        form_controls = page.locator("form input, form select, form textarea").count()
    except Exception:
        return False
    return credential_controls == 0 and form_controls >= 5


@dataclass
class PortalSessionManager:
    data_root: Path
    portal_url: str = DEFAULT_PORTAL_URL

    @property
    def profile_dir(self) -> Path:
        return self.data_root / "portal-browser-profile"

    @property
    def snapshot_path(self) -> Path:
        return self.data_root / "portal-session.json"

    def _prepare_profile(self) -> None:
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        try:
            self.profile_dir.chmod(0o700)
        except OSError:
            pass

    def _save_snapshot(self, snapshot: PortalSessionSnapshot) -> None:
        content = (
            json.dumps(snapshot.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
        CaseStore._atomic_write(self.snapshot_path, content)

    def open_for_login(
        self,
        *,
        timeout_seconds: float = 600,
        poll_seconds: float = 1,
    ) -> PortalSessionSnapshot:
        validate_portal_url(self.portal_url)
        self._prepare_profile()
        deadline = time.monotonic() + timeout_seconds
        last_location = safe_portal_location(self.portal_url)

        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir),
                headless=False,
                viewport=None,
            )
            try:
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(self.portal_url, wait_until="domcontentloaded")

                while True:
                    last_location = safe_portal_location(page.url)
                    if is_authenticated_form_c(page):
                        snapshot = PortalSessionSnapshot(
                            state=PortalSessionState.READY,
                            portal_location=last_location,
                            message="Authenticated Form C controls detected",
                        )
                        self._save_snapshot(snapshot)
                        return snapshot
                    if time.monotonic() >= deadline:
                        break
                    time.sleep(poll_seconds)

                snapshot = PortalSessionSnapshot(
                    state=PortalSessionState.NEEDS_LOGIN,
                    portal_location=last_location,
                    message="Login or CAPTCHA was not completed before the timeout",
                )
                self._save_snapshot(snapshot)
                return snapshot
            finally:
                context.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Open or renew Yeratta's authorised Form C browser session"
    )
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument(
        "--portal-url",
        default=os.environ.get("FORMC_PORTAL_URL", DEFAULT_PORTAL_URL),
        help="Fresh official Form C URL; query parameters are never written to disk",
    )
    parser.add_argument("--timeout", type=float, default=600)
    args = parser.parse_args()

    print("A dedicated Chromium window will open.")
    print("Complete the normal government login and CAPTCHA in that window.")
    snapshot = PortalSessionManager(
        data_root=args.data_dir,
        portal_url=args.portal_url,
    ).open_for_login(timeout_seconds=args.timeout)
    print(f"Portal session: {snapshot.state}")
    print(snapshot.message)
    if snapshot.state != PortalSessionState.READY:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
