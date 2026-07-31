from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from formc_app.portal_session import (
    PortalSessionManager,
    PortalSessionState,
    is_authenticated_form_c,
    safe_portal_location,
    validate_portal_url,
)


class FakeLocator:
    def __init__(self, count: int):
        self._count = count

    def count(self) -> int:
        return self._count


class FakePage:
    def __init__(
        self,
        *,
        url: str,
        credential_controls: int = 0,
        form_controls: int = 12,
    ):
        self.url = url
        self.credential_controls = credential_controls
        self.form_controls = form_controls

    def locator(self, selector: str) -> FakeLocator:
        count = (
            self.credential_controls
            if 'input[type="password"]' in selector
            else self.form_controls
        )
        return FakeLocator(count)

    def goto(self, url: str, **_kwargs) -> None:
        self.url = url


class FakeContext:
    def __init__(self, page: FakePage):
        self.pages = [page]
        self.closed = False
        self.playwright_stopped = False

    def new_page(self) -> FakePage:
        raise AssertionError("The existing persistent-profile page should be reused")

    def close(self) -> None:
        if self.playwright_stopped:
            raise RuntimeError("Event loop is closed")
        self.closed = True


class FakePlaywrightContext:
    def __init__(self, context: FakeContext):
        self.context = context
        self.value = SimpleNamespace(
            chromium=SimpleNamespace(
                launch_persistent_context=lambda **_kwargs: self.context
            )
        )

    def __enter__(self):
        return self.value

    def __exit__(self, *_args):
        self.context.playwright_stopped = True
        return None


def test_authenticated_form_requires_official_https_form_and_no_login_controls():
    assert is_authenticated_form_c(
        FakePage(url="https://indianfrro.gov.in/frro/FormC/formc.jsp?t4g=secret")
    )
    assert not is_authenticated_form_c(
        FakePage(
            url="https://indianfrro.gov.in/frro/FormC/formc.jsp",
            credential_controls=1,
        )
    )
    assert not is_authenticated_form_c(
        FakePage(url="https://example.com/frro/FormC/formc.jsp")
    )
    assert not is_authenticated_form_c(
        FakePage(
            url="https://indianfrro.gov.in/frro/FormC/formc.jsp",
            form_controls=2,
        )
    )


def test_safe_location_removes_session_like_query_and_fragment():
    assert safe_portal_location(
        "https://indianfrro.gov.in/frro/FormC/formc.jsp?t4g=secret#section"
    ) == "https://indianfrro.gov.in/frro/FormC/formc.jsp"


@pytest.mark.parametrize(
    "url",
    [
        "http://indianfrro.gov.in/frro/FormC",
        "https://example.com/frro/FormC",
        "https://indianfrro.gov.in.evil.example/frro/FormC",
        "https://indianfrro.gov.in/frro/FormC-lookalike",
        "https://user:password@indianfrro.gov.in/frro/FormC",
    ],
)
def test_portal_url_must_be_the_official_https_form_c_surface(url: str):
    with pytest.raises(ValueError, match="official HTTPS Form C portal"):
        validate_portal_url(url)


def test_manager_rejects_unofficial_url_before_creating_profile(tmp_path: Path):
    manager = PortalSessionManager(
        data_root=tmp_path,
        portal_url="https://example.com/frro/FormC",
    )

    with pytest.raises(ValueError, match="official HTTPS Form C portal"):
        manager.open_for_login(timeout_seconds=0, poll_seconds=0)

    assert not manager.profile_dir.exists()


def test_manager_uses_persistent_profile_and_writes_redacted_ready_snapshot(
    tmp_path: Path,
    monkeypatch,
):
    portal_url = "https://indianfrro.gov.in/frro/FormC/formc.jsp?t4g=secret"
    page = FakePage(url=portal_url)
    context = FakeContext(page)
    launch_arguments = {}
    fake_playwright = FakePlaywrightContext(context)

    def launch_persistent_context(**kwargs):
        launch_arguments.update(kwargs)
        return context

    fake_playwright.value.chromium.launch_persistent_context = launch_persistent_context
    monkeypatch.setattr(
        "formc_app.portal_session.sync_playwright",
        lambda: fake_playwright,
    )

    snapshot = PortalSessionManager(
        data_root=tmp_path,
        portal_url=portal_url,
    ).open_for_login(timeout_seconds=0, poll_seconds=0)

    assert snapshot.state == PortalSessionState.READY
    assert snapshot.portal_location.endswith("/frro/FormC/formc.jsp")
    assert "secret" not in snapshot.portal_location
    assert launch_arguments["headless"] is False
    assert Path(launch_arguments["user_data_dir"]) == tmp_path / "portal-browser-profile"
    assert context.closed
    persisted = json.loads((tmp_path / "portal-session.json").read_text("utf-8"))
    assert persisted["state"] == "READY"
    assert "secret" not in json.dumps(persisted)


def test_manager_runs_authenticated_action_before_closing_browser(
    tmp_path: Path,
    monkeypatch,
):
    page = FakePage(
        url="https://indianfrro.gov.in/frro/FormC/formc.jsp?t4g=secret"
    )
    context = FakeContext(page)
    fake_playwright = FakePlaywrightContext(context)
    monkeypatch.setattr(
        "formc_app.portal_session.sync_playwright",
        lambda: fake_playwright,
    )
    events = []

    def authenticated_action(authenticated_page):
        assert authenticated_page is page
        assert not context.closed
        assert not context.playwright_stopped
        events.append("catalogued")

    snapshot = PortalSessionManager(data_root=tmp_path).open_for_login(
        timeout_seconds=0,
        poll_seconds=0,
        on_authenticated=authenticated_action,
    )

    assert snapshot.state == PortalSessionState.READY
    assert events == ["catalogued"]
    assert context.closed
    assert context.playwright_stopped


def test_manager_records_needs_login_without_persisting_query_token(
    tmp_path: Path,
    monkeypatch,
):
    portal_url = "https://indianfrro.gov.in/frro/FormC/formc.jsp?t4g=secret"
    page = FakePage(url=portal_url, credential_controls=1)
    context = FakeContext(page)
    monkeypatch.setattr(
        "formc_app.portal_session.sync_playwright",
        lambda: FakePlaywrightContext(context),
    )

    snapshot = PortalSessionManager(
        data_root=tmp_path,
        portal_url=portal_url,
    ).open_for_login(timeout_seconds=0, poll_seconds=0)

    assert snapshot.state == PortalSessionState.NEEDS_LOGIN
    assert context.closed
    assert "secret" not in (tmp_path / "portal-session.json").read_text("utf-8")
