from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from formc_app.portal_catalogue import (
    PortalCatalogueManager,
    catalogue_page_controls,
    safe_controls,
)


class FakeCatalogueLocator:
    def __init__(self, controls, *, count_override=None):
        self.controls = controls
        self.count_override = count_override

    def count(self) -> int:
        return self.count_override if self.count_override is not None else len(self.controls)

    def evaluate_all(self, _script):
        return self.controls


class FakeCataloguePage:
    def __init__(self, controls):
        self.url = "https://indianfrro.gov.in/frro/FormC/formc.jsp?t4g=secret"
        self.controls = controls

    def locator(self, selector: str):
        if 'input[type="password"]' in selector:
            return FakeCatalogueLocator([])
        if selector == "form input, form select, form textarea":
            return FakeCatalogueLocator(self.controls, count_override=12)
        return FakeCatalogueLocator(self.controls)

    def goto(self, url: str, **_kwargs):
        self.url = (
            "https://indianfrro.gov.in/frro/FormC/formc.jsp?t4g=secret"
            if url.startswith("https://indianfrro.gov.in/frro/FormC")
            else url
        )


class FakeCatalogueContext:
    def __init__(self, page):
        self.pages = [page]
        self.closed = False

    def new_page(self):
        raise AssertionError("The persistent-profile page should be reused")

    def close(self):
        self.closed = True


class FakePlaywrightContext:
    def __init__(self, browser_context):
        self.value = SimpleNamespace(
            chromium=SimpleNamespace(
                launch_persistent_context=lambda **_kwargs: browser_context
            )
        )

    def __enter__(self):
        return self.value

    def __exit__(self, *_args):
        return None


def sample_controls():
    return [
        {
            "ordinal": 0,
            "tag": "input",
            "name": "surname",
            "element_id": "surname",
            "input_type": "text",
            "label": "Surname",
            "required": True,
            "disabled": False,
            "read_only": False,
            "multiple": False,
            "options": [],
            "value": "MUST NOT BE PERSISTED",
        },
        {
            "ordinal": 1,
            "tag": "input",
            "name": "csrf_token",
            "element_id": "csrf_token",
            "input_type": "hidden",
            "label": None,
            "required": False,
            "disabled": False,
            "read_only": False,
            "multiple": False,
            "options": [],
        },
        {
            "ordinal": 2,
            "tag": "select",
            "name": "nationality",
            "element_id": "nationality",
            "input_type": None,
            "label": "Nationality",
            "required": True,
            "disabled": False,
            "read_only": False,
            "multiple": False,
            "options": [
                {"label": "Select", "value": "", "disabled": False},
                {"label": "United Kingdom", "value": "826", "disabled": False},
            ],
        },
        {
            "ordinal": 3,
            "tag": "input",
            "name": "captchaAnswer",
            "element_id": "captchaAnswer",
            "input_type": "text",
            "label": "CAPTCHA",
            "required": True,
            "disabled": False,
            "read_only": False,
            "multiple": False,
            "options": [],
        },
    ]


def test_safe_controls_excludes_values_hidden_and_credential_like_controls():
    controls = safe_controls(sample_controls())

    assert [control.name for control in controls] == ["surname", "nationality"]
    serialized = json.dumps([control.model_dump(mode="json") for control in controls])
    assert "MUST NOT BE PERSISTED" not in serialized
    assert "csrf" not in serialized.lower()
    assert "captcha" not in serialized.lower()
    assert controls[1].options[1].value == "826"


def test_catalogue_page_controls_only_evaluates_the_read_only_selector():
    page = FakeCataloguePage(sample_controls())

    controls = catalogue_page_controls(page)

    assert [control.name for control in controls] == ["surname", "nationality"]


def test_manager_uses_existing_profile_and_writes_redacted_catalogue(
    tmp_path: Path,
    monkeypatch,
):
    profile_dir = tmp_path / "portal-browser-profile"
    profile_dir.mkdir()
    page = FakeCataloguePage(sample_controls())
    browser_context = FakeCatalogueContext(page)
    monkeypatch.setattr(
        "formc_app.portal_catalogue.sync_playwright",
        lambda: FakePlaywrightContext(browser_context),
    )

    catalogue = PortalCatalogueManager(data_root=tmp_path).catalogue()

    assert catalogue.control_count == 2
    assert browser_context.closed
    persisted = (tmp_path / "portal-controls.json").read_text("utf-8")
    assert "t4g" not in persisted
    assert "secret" not in persisted
    assert "MUST NOT BE PERSISTED" not in persisted


def test_manager_requires_the_login_profile(tmp_path: Path):
    manager = PortalCatalogueManager(data_root=tmp_path)

    try:
        manager.catalogue()
    except RuntimeError as error:
        assert "formc-portal-login" in str(error)
    else:
        raise AssertionError("Catalogue should require an existing login profile")
