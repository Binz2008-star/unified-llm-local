"""P1.1: Tests for typed Settings."""

import os

import pytest

from app_settings import Settings, reload_settings, validate_production_settings


class TestSettingsDefaults:
    def test_auto_commit_default_false(self):
        s = Settings()
        assert s.auto_commit is False

    def test_require_human_approval_default_true(self):
        s = Settings()
        assert s.require_human_approval is True

    def test_allow_network_default_false(self):
        s = Settings()
        assert s.allow_network is False

    def test_allow_destructive_commands_default_false(self):
        s = Settings()
        assert s.allow_destructive_commands is False

    def test_command_timeout_default_120(self):
        s = Settings()
        assert s.command_timeout_seconds == 120

    def test_max_tool_calls_default_30(self):
        s = Settings()
        assert s.max_tool_calls == 30

    def test_models_non_empty(self):
        s = Settings()
        assert s.architect_model
        assert s.editor_model
        assert s.tester_model
        assert s.chat_model

    def test_ollama_base_url_default(self):
        s = Settings()
        assert s.ollama_base_url == "http://127.0.0.1:11434"

    def test_ollama_embed_url_derived(self):
        s = Settings()
        assert s.ollama_embed_url == "http://127.0.0.1:11434/api/embed"

    def test_ollama_chat_url_derived(self):
        s = Settings()
        assert s.ollama_chat_url == "http://127.0.0.1:11434/api/chat"


class TestSettingsValidation:
    def test_empty_model_rejected(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            Settings(architect_model="")

    def test_whitespace_model_rejected(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            Settings(editor_model="   ")

    def test_timeout_too_low_rejected(self):
        with pytest.raises(ValueError):
            Settings(command_timeout_seconds=0)

    def test_timeout_too_high_rejected(self):
        with pytest.raises(ValueError):
            Settings(command_timeout_seconds=99999)

    def test_max_tool_calls_too_low_rejected(self):
        with pytest.raises(ValueError):
            Settings(max_tool_calls=0)

    def test_embed_dim_range(self):
        with pytest.raises(ValueError):
            Settings(embed_dim=0)


class TestProductionValidation:
    def test_auto_commit_without_approval_is_critical(self):
        s = Settings(auto_commit=True, require_human_approval=False)
        issues = validate_production_settings(s)
        assert any("CRITICAL" in i for i in issues)

    def test_destructive_commands_warning(self):
        s = Settings(allow_destructive_commands=True)
        issues = validate_production_settings(s)
        assert any("WARNING" in i for i in issues)

    def test_safe_settings_no_issues(self):
        s = Settings()
        issues = validate_production_settings(s)
        assert len(issues) == 0


class TestReload:
    def test_reload_returns_fresh_instance(self):
        s1 = reload_settings()
        s2 = reload_settings()
        assert s1 is not s2


class TestEnvOverride:
    def test_auto_commit_from_env(self, monkeypatch):
        monkeypatch.setenv("AUTO_COMMIT", "true")
        reload_settings()
        s = Settings()
        assert s.auto_commit is True
        reload_settings()
