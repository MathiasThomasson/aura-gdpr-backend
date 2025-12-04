import importlib

from app.core import config


def test_is_platform_owner_email_matches_case_insensitive(monkeypatch):
    monkeypatch.setattr(config.settings, "PLATFORM_OWNER_EMAILS", "owner@example.com, second@domain.com")
    config._platform_owner_email_set.cache_clear()
    assert config.is_platform_owner_email("Owner@Example.com") is True
    assert config.is_platform_owner_email("SECOND@domain.com") is True
    assert config.is_platform_owner_email("unknown@example.com") is False


def test_is_platform_owner_email_empty_config(monkeypatch):
    monkeypatch.setattr(config.settings, "PLATFORM_OWNER_EMAILS", None)
    monkeypatch.setattr(config.settings, "PLATFORM_ADMIN_EMAIL", "admin@aura-gdpr.se")
    config._platform_owner_email_set.cache_clear()
    assert config.is_platform_owner_email("owner@example.com") is False


def test_is_platform_owner_admin_email(monkeypatch):
    monkeypatch.setattr(config.settings, "PLATFORM_OWNER_EMAILS", None)
    monkeypatch.setattr(config.settings, "PLATFORM_ADMIN_EMAIL", "admin@aura-gdpr.se")
    config._platform_owner_email_set.cache_clear()
    assert config.is_platform_owner_email("admin@aura-gdpr.se") is True
