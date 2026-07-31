from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from playwright.sync_api import Page, sync_playwright
from pydantic import BaseModel, ConfigDict, Field

from formc_app.models import utc_now
from formc_app.portal_session import (
    DEFAULT_PORTAL_URL,
    is_authenticated_form_c,
    safe_portal_location,
    validate_portal_url,
)
from formc_app.storage import CaseStore


CONTROL_SCRIPT = r"""
(elements) => elements.map((element, ordinal) => {
  const clean = (value) => {
    if (!value) return null;
    const collapsed = value.replace(/\s+/g, " ").trim();
    return collapsed ? collapsed.slice(0, 200) : null;
  };
  const tag = element.tagName.toLowerCase();
  const id = element.getAttribute("id");
  const associatedLabel = id
    ? document.querySelector(`label[for="${CSS.escape(id)}"]`)
    : null;
  const wrappingLabel = element.closest("label");
  const cell = element.closest("td, th");
  const precedingCell = cell ? cell.previousElementSibling : null;
  const label = clean(
    associatedLabel?.innerText ||
    wrappingLabel?.innerText ||
    element.getAttribute("aria-label") ||
    element.getAttribute("placeholder") ||
    (tag === "button" ? element.innerText : null) ||
    precedingCell?.innerText
  );
  return {
    ordinal,
    tag,
    name: element.getAttribute("name"),
    element_id: id,
    input_type: element.getAttribute("type"),
    label,
    required: Boolean(element.required) || element.getAttribute("aria-required") === "true",
    disabled: Boolean(element.disabled),
    read_only: Boolean(element.readOnly),
    multiple: Boolean(element.multiple),
    options: tag === "select"
      ? Array.from(element.options).map((option) => ({
          label: clean(option.textContent) || "",
          value: String(option.value).slice(0, 200),
          disabled: Boolean(option.disabled),
        }))
      : [],
  };
})
"""

SENSITIVE_CONTROL_MARKERS = (
    "captcha",
    "csrf",
    "password",
    "passwd",
    "session",
    "t4g",
    "token",
)


class PortalOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    value: str
    disabled: bool = False


class PortalControl(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ordinal: int
    tag: Literal["input", "select", "textarea", "button"]
    name: str | None = None
    element_id: str | None = None
    input_type: str | None = None
    label: str | None = None
    required: bool = False
    disabled: bool = False
    read_only: bool = False
    multiple: bool = False
    options: list[PortalOption] = Field(default_factory=list)


class PortalControlCatalogue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    captured_at: datetime = Field(default_factory=utc_now)
    portal_location: str
    control_count: int
    controls: list[PortalControl]


def _clean_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split()).strip()[:200]
    return cleaned or None


def safe_controls(raw_controls: list[dict[str, Any]]) -> list[PortalControl]:
    """Validate structural metadata while dropping credential-like controls."""
    controls: list[PortalControl] = []
    for raw in raw_controls:
        tag = str(raw.get("tag", "")).lower()
        input_type = _clean_text(raw.get("input_type"))
        name = _clean_text(raw.get("name"))
        element_id = _clean_text(raw.get("element_id"))
        identifiers = " ".join(
            part.lower() for part in (name, element_id, input_type) if part
        )
        if tag not in {"input", "select", "textarea", "button"}:
            continue
        if input_type and input_type.lower() in {"hidden", "password"}:
            continue
        if any(marker in identifiers for marker in SENSITIVE_CONTROL_MARKERS):
            continue

        options: list[PortalOption] = []
        if tag == "select":
            for option in raw.get("options", []):
                if not isinstance(option, dict):
                    continue
                options.append(
                    PortalOption(
                        label=_clean_text(option.get("label")) or "",
                        value=_clean_text(option.get("value")) or "",
                        disabled=bool(option.get("disabled", False)),
                    )
                )

        controls.append(
            PortalControl(
                ordinal=int(raw.get("ordinal", len(controls))),
                tag=tag,
                name=name,
                element_id=element_id,
                input_type=input_type,
                label=_clean_text(raw.get("label")),
                required=bool(raw.get("required", False)),
                disabled=bool(raw.get("disabled", False)),
                read_only=bool(raw.get("read_only", False)),
                multiple=bool(raw.get("multiple", False)),
                options=options,
            )
        )
    return controls


def catalogue_page_controls(page: Page) -> list[PortalControl]:
    raw_controls = page.locator(
        'form input:not([type="hidden"]):not([type="password"]), '
        "form select, form textarea, form button"
    ).evaluate_all(CONTROL_SCRIPT)
    if not isinstance(raw_controls, list):
        raise RuntimeError("Portal returned an unexpected control structure")
    return safe_controls(raw_controls)


@dataclass
class PortalCatalogueManager:
    data_root: Path
    portal_url: str = DEFAULT_PORTAL_URL

    @property
    def profile_dir(self) -> Path:
        return self.data_root / "portal-browser-profile"

    @property
    def catalogue_path(self) -> Path:
        return self.data_root / "portal-controls.json"

    def catalogue(self) -> PortalControlCatalogue:
        validate_portal_url(self.portal_url)
        if not self.profile_dir.is_dir():
            raise RuntimeError("Run formc-portal-login before cataloguing controls")

        context = None
        try:
            with sync_playwright() as playwright:
                context = playwright.chromium.launch_persistent_context(
                    user_data_dir=str(self.profile_dir),
                    headless=False,
                    viewport=None,
                )
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(self.portal_url, wait_until="domcontentloaded")
                if not is_authenticated_form_c(page):
                    raise RuntimeError(
                        "Authenticated Form C controls were not found; renew the portal session"
                    )
                controls = catalogue_page_controls(page)
                if not controls:
                    raise RuntimeError("No safe Form C controls were found")
                catalogue = PortalControlCatalogue(
                    portal_location=safe_portal_location(page.url),
                    control_count=len(controls),
                    controls=controls,
                )
                content = (
                    json.dumps(
                        catalogue.model_dump(mode="json"),
                        indent=2,
                        sort_keys=True,
                    )
                    + "\n"
                ).encode("utf-8")
                CaseStore._atomic_write(self.catalogue_path, content)
                return catalogue
        finally:
            if context is not None:
                context.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read safe structural metadata from the authenticated Form C page"
    )
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument(
        "--portal-url",
        default=os.environ.get("FORMC_PORTAL_URL", DEFAULT_PORTAL_URL),
        help="Official Form C URL; query parameters are never written to disk",
    )
    args = parser.parse_args()

    print("Read-only catalogue: no controls will be filled, clicked or submitted.")
    catalogue = PortalCatalogueManager(
        data_root=args.data_dir,
        portal_url=args.portal_url,
    ).catalogue()
    print(f"Catalogued {catalogue.control_count} safe controls")
    print(f"Saved {args.data_dir / 'portal-controls.json'}")


if __name__ == "__main__":
    main()
