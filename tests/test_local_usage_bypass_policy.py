from types import SimpleNamespace
from typing import cast

from fastapi import HTTPException

from api.services.local_usage import (
    LocalUsageContext,
    has_weekly_recap_feature_access,
    is_local_usage_bypass_enabled,
    is_usage_safety_bypass_enabled,
    require_weekly_recap_access,
)
from api.services.local_usage_plans import LOCAL_DEFAULT_USAGE_PLAN, LocalUsagePlan


def test_local_usage_bypass_enabled_when_flag_is_true(monkeypatch):
    monkeypatch.setenv("WEB_APP_URL", "http://localhost:3000")

    assert is_local_usage_bypass_enabled(
        SimpleNamespace(local_usage_dev_bypass=True, web_app_url="http://localhost:3000")
    ) is True


def test_local_usage_bypass_disabled_in_local_auth_mode_without_flag(monkeypatch):
    monkeypatch.setenv("WEB_APP_URL", "https://test.paced.coach")

    assert (
        is_local_usage_bypass_enabled(
            SimpleNamespace(auth_mode="local", local_usage_dev_bypass=False, web_app_url="https://test.paced.coach")
        )
        is False
    )


def test_usage_safety_bypass_disabled_by_default_in_local_auth_mode(monkeypatch):
    monkeypatch.setenv("WEB_APP_URL", "https://test.paced.coach")

    assert (
        is_usage_safety_bypass_enabled(
            SimpleNamespace(
                auth_mode="local",
                local_usage_safety_bypass=False,
                local_usage_dev_bypass=False,
                web_app_url="https://test.paced.coach",
            )
        )
        is False
    )


def test_usage_safety_bypass_can_be_explicitly_enabled_in_local_auth_mode(monkeypatch):
    monkeypatch.setenv("WEB_APP_URL", "https://test.paced.coach")

    assert (
        is_usage_safety_bypass_enabled(
            SimpleNamespace(
                auth_mode="local",
                local_usage_safety_bypass=True,
                local_usage_dev_bypass=False,
                web_app_url="https://test.paced.coach",
            )
        )
        is True
    )


def test_local_usage_bypass_is_disabled_for_staging_without_flag(monkeypatch):
    monkeypatch.setenv("WEB_APP_URL", "https://test.paced.coach")

    assert is_local_usage_bypass_enabled(
        SimpleNamespace(local_usage_dev_bypass=False, web_app_url="https://test.paced.coach")
    ) is False


def test_local_usage_bypass_is_disabled_when_flag_is_true_but_url_is_not_localhost(monkeypatch):
    monkeypatch.setenv("WEB_APP_URL", "https://test.paced.coach")

    assert is_local_usage_bypass_enabled(
        SimpleNamespace(local_usage_dev_bypass=True, web_app_url="https://test.paced.coach")
    ) is False


def test_local_usage_bypass_disabled_for_production_without_flag(monkeypatch):
    monkeypatch.setenv("WEB_APP_URL", "https://paced.coach")

    assert is_local_usage_bypass_enabled(
        SimpleNamespace(local_usage_dev_bypass=False, web_app_url="https://paced.coach")
    ) is False


def test_local_usage_bypass_is_disabled_when_web_app_url_falls_back_to_default(monkeypatch):
    monkeypatch.delenv("WEB_APP_URL", raising=False)

    assert is_local_usage_bypass_enabled(
        SimpleNamespace(local_usage_dev_bypass=True, web_app_url="http://localhost:3000")
    ) is False


def test_weekly_recap_feature_access_honors_dev_bypass(monkeypatch):
    monkeypatch.setenv("WEB_APP_URL", "http://localhost:3000")

    context = LocalUsageContext(
        plan_override=None,
        selected_plan=None,
        effective_plan=LOCAL_DEFAULT_USAGE_PLAN,
        tier="free",
        has_access=False,
    )

    assert has_weekly_recap_feature_access(
        context,
        SimpleNamespace(local_usage_dev_bypass=True, web_app_url="http://localhost:3000"),
    )


def test_require_weekly_recap_access_still_blocks_without_bypass():
    context = LocalUsageContext(
        plan_override=None,
        selected_plan=None,
        effective_plan=cast("LocalUsagePlan", SimpleNamespace(weekly_recap_included=False)),
        tier="free",
        has_access=False,
    )

    try:
        require_weekly_recap_access(
            context,
            SimpleNamespace(local_usage_dev_bypass=False, web_app_url="https://test.paced.coach"),
        )
    except HTTPException as exc:
        assert exc.status_code == 403
        assert exc.detail == "Weekly recap is not available"
    else:
        raise AssertionError("Expected weekly recap access check to fail without bypass")
