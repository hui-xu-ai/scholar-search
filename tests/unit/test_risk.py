from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from scholar_search.core.contracts import Action, ActionOutcome, RiskSignal
from scholar_search.core.errors import RiskBlocked
from scholar_search.core.risk import RiskGuard


def outcome(
    *,
    data: dict[str, str] | None = None,
    error: str | None = None,
    url: str | None = None,
) -> ActionOutcome:
    return ActionOutcome(
        action=Action("read_html"),
        ok=error is None,
        data=data or {},
        error=error,
        url=url,
    )


def guard(tmp_path: Path) -> RiskGuard:
    return RiskGuard(state_path=tmp_path / "cooldown.json")


def test_detects_visible_captcha_widget(tmp_path: Path) -> None:
    signal = guard(tmp_path).inspect(outcome(data={"captcha_visible": True}))
    assert signal is RiskSignal.CAPTCHA


def test_hidden_sdk_dom_is_not_a_captcha(tmp_path: Path) -> None:
    # The captcha SDK preloads DOM; text alone must not trigger a cooldown.
    assert guard(tmp_path).inspect(outcome(data={"html": "验证码登录"})) is None
    assert guard(tmp_path).inspect(outcome(data={"captcha_visible": False})) is None


def test_verification_page_title_is_a_risk(tmp_path: Path) -> None:
    signal = guard(tmp_path).inspect(outcome(data={"title": "安全验证"}))
    assert signal is RiskSignal.VERIFY_REDIRECT


def test_account_verification_gate_is_a_login_wall(tmp_path: Path) -> None:
    signal = guard(tmp_path).inspect(outcome(data={"auth_required": True}))
    assert signal is RiskSignal.LOGIN_REDIRECT


def test_detects_verify_redirect(tmp_path: Path) -> None:
    signal = guard(tmp_path).inspect(
        outcome(url="https://kns.cnki.net/verify/home?x=1")
    )
    assert signal is RiskSignal.VERIFY_REDIRECT


def test_detects_http_403(tmp_path: Path) -> None:
    signal = guard(tmp_path).inspect(outcome(error="http 403 forbidden"))
    assert signal is RiskSignal.HTTP_403


def test_detects_login_redirect(tmp_path: Path) -> None:
    signal = guard(tmp_path).inspect(outcome(url="https://fsso.cnki.net/login"))
    assert signal is RiskSignal.LOGIN_REDIRECT


def test_clean_outcome_has_no_signal(tmp_path: Path) -> None:
    assert guard(tmp_path).inspect(outcome(data={"html": "<html>ok</html>"})) is None


def test_trip_sets_cooldown_and_blocks(tmp_path: Path) -> None:
    risk = guard(tmp_path)
    blocked = risk.trip(RiskSignal.CAPTCHA, "captcha appeared")

    assert blocked.signal == "captcha"
    assert blocked.to_payload()["action_required"] == "manual_verification"
    with pytest.raises(RiskBlocked):
        risk.ensure_ready()


def test_expired_cooldown_is_ignored(tmp_path: Path) -> None:
    path = tmp_path / "cooldown.json"
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    path.write_text(f'{{"until": "{past.isoformat()}", "signal": "captcha"}}', encoding="utf-8")

    risk = RiskGuard(state_path=path)
    risk.ensure_ready()  # must not raise


def test_clear_removes_cooldown(tmp_path: Path) -> None:
    risk = guard(tmp_path)
    risk.trip(RiskSignal.VERIFY_REDIRECT)
    risk.clear()
    risk.ensure_ready()
