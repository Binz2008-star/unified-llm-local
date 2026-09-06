"""SEC-05: Comprehensive tests for protected path policy."""

import logging
from pathlib import Path

import pytest

from protected_path_policy import (
    ALLOWED_TASK_ENV_KEYS,
    PROTECTED_BASENAMES,
    PROTECTED_SUFFIXES,
    WRITEABLE_TEMPLATES,
    ProtectedPathError,
    assert_mutation_allowed,
    build_runtime_env,
    contains_secret_content,
    copy_file,
    delete_file,
    is_protected_path,
    is_writeable_template,
    rename_file,
    scrub_secrets,
    validate_file_content,
)
from tool_security import apply_patch, write_file


class TestProtectedPathDetection:
    def test_env_protected(self):
        assert is_protected_path(Path(".env"))

    def test_env_local_protected(self):
        assert is_protected_path(Path(".env.local"))

    def test_env_production_protected(self):
        assert is_protected_path(Path(".env.production"))

    def test_env_prod_protected(self):
        assert is_protected_path(Path(".env.prod"))

    def test_env_staging_protected(self):
        assert is_protected_path(Path(".env.staging"))

    def test_credentials_json_protected(self):
        assert is_protected_path(Path("credentials.json"))

    def test_secrets_json_protected(self):
        assert is_protected_path(Path("secrets.json"))

    def test_token_json_protected(self):
        assert is_protected_path(Path("token.json"))

    def test_pem_file_protected(self):
        assert is_protected_path(Path("server.pem"))

    def test_key_file_protected(self):
        assert is_protected_path(Path("private.key"))

    def test_id_rsa_protected(self):
        assert is_protected_path(Path("id_rsa"))

    def test_id_ed25519_protected(self):
        assert is_protected_path(Path("id_ed25519"))

    def test_env_in_subdir_protected(self):
        assert is_protected_path(Path("config/.env"))

    def test_env_case_insensitive(self):
        assert is_protected_path(Path(".ENV"))
        assert is_protected_path(Path(".Env"))

    def test_normal_file_not_protected(self):
        assert not is_protected_path(Path("main.py"))
        assert not is_protected_path(Path("README.md"))

    def test_env_example_not_protected(self):
        assert not is_protected_path(Path(".env.example"))


class TestTemplateProtection:
    def test_env_example_only_writable(self):
        """Templates should only be writable, not deletable/renamed/copied."""
        template = Path(".env.example")

        # Write should be allowed
        assert_mutation_allowed(template, "write", allow_template_write=True)

        # Delete should be blocked
        with pytest.raises(ProtectedPathError, match="template mutation"):
            assert_mutation_allowed(template, "delete")

        # Rename should be blocked
        with pytest.raises(ProtectedPathError, match="template mutation"):
            assert_mutation_allowed(template, "rename")

        # Copy should be blocked
        with pytest.raises(ProtectedPathError, match="template mutation"):
            assert_mutation_allowed(template, "copy")

        # Patch should be blocked
        with pytest.raises(ProtectedPathError, match="template mutation"):
            assert_mutation_allowed(template, "patch")

    def test_env_template_only_writable(self):
        template = Path(".env.template")

        assert_mutation_allowed(template, "write", allow_template_write=True)

        with pytest.raises(ProtectedPathError):
            assert_mutation_allowed(template, "delete")

    def test_env_sample_only_writable(self):
        template = Path(".env.sample")

        assert_mutation_allowed(template, "write", allow_template_write=True)

        with pytest.raises(ProtectedPathError):
            assert_mutation_allowed(template, "rename")


class TestWriteProtection:
    def test_write_dotenv_rejected(self, tmp_path):
        with pytest.raises(ProtectedPathError, match="protected"):
            assert_mutation_allowed(tmp_path / ".env", "write")

    def test_write_env_production_rejected(self, tmp_path):
        with pytest.raises(ProtectedPathError, match="protected"):
            assert_mutation_allowed(tmp_path / ".env.production", "write")

    def test_write_credentials_rejected(self, tmp_path):
        with pytest.raises(ProtectedPathError, match="protected"):
            assert_mutation_allowed(tmp_path / "credentials.json", "write")

    def test_write_file_tool_blocks_dotenv(self, tmp_path):
        with pytest.raises(ProtectedPathError):
            write_file(".env", "SECRET=abc", tmp_path)

    def test_write_file_tool_blocks_nested_dotenv(self, tmp_path):
        with pytest.raises(ProtectedPathError):
            write_file("config/.env", "SECRET=abc", tmp_path)

    def test_write_file_tool_allows_normal(self, tmp_path):
        result = write_file("main.py", "print('hello')", tmp_path)
        assert "Wrote" in result


class TestDeleteProtection:
    def test_delete_dotenv_rejected(self, tmp_path):
        with pytest.raises(ProtectedPathError, match="protected"):
            delete_file(".env", tmp_path)

    def test_delete_secrets_rejected(self, tmp_path):
        with pytest.raises(ProtectedPathError, match="protected"):
            delete_file("secrets.json", tmp_path)

    def test_delete_env_example_rejected(self, tmp_path):
        """Templates can only be written, not deleted."""
        (tmp_path / ".env.example").write_text("KEY=value")
        with pytest.raises(ProtectedPathError, match="template mutation"):
            delete_file(".env.example", tmp_path)


class TestRenameProtection:
    def test_rename_to_dotenv_rejected(self, tmp_path):
        (tmp_path / "safe.txt").write_text("content")
        with pytest.raises(ProtectedPathError, match="protected"):
            rename_file("safe.txt", ".env", tmp_path)

    def test_rename_from_dotenv_rejected(self, tmp_path):
        (tmp_path / ".env").write_text("SECRET=value")
        with pytest.raises(ProtectedPathError, match="protected"):
            rename_file(".env", "backup.txt", tmp_path)

    def test_rename_protected_to_protected_rejected(self, tmp_path):
        (tmp_path / ".env").write_text("SECRET=old")
        with pytest.raises(ProtectedPathError, match="protected"):
            rename_file(".env", ".env.backup", tmp_path)

    def test_rename_normal_allowed(self, tmp_path):
        (tmp_path / "old.py").write_text("code")
        result = rename_file("old.py", "new.py", tmp_path)
        assert "Renamed" in result


class TestCopyProtection:
    def test_copy_to_dotenv_rejected(self, tmp_path):
        (tmp_path / "safe.txt").write_text("content")
        with pytest.raises(ProtectedPathError, match="protected"):
            copy_file("safe.txt", ".env", tmp_path)

    def test_copy_from_dotenv_rejected(self, tmp_path):
        (tmp_path / ".env").write_text("SECRET=value")
        with pytest.raises(ProtectedPathError, match="protected"):
            copy_file(".env", "backup.txt", tmp_path)

    def test_copy_normal_allowed(self, tmp_path):
        (tmp_path / "source.py").write_text("code")
        result = copy_file("source.py", "dest.py", tmp_path)
        assert "Copied" in result


class TestTraversalProtection:
    def test_traversal_to_dotenv_rejected(self, tmp_path):
        with pytest.raises(ProtectedPathError):
            assert_mutation_allowed(tmp_path / "config" / ".." / ".env", "write")

    def test_deep_traversal_rejected(self, tmp_path):
        with pytest.raises(ProtectedPathError):
            assert_mutation_allowed(
                tmp_path / "a" / "b" / "c" / ".." / ".." / ".." / ".env", "write"
            )


class TestSecretContentDetection:
    def test_api_key_detected(self):
        assert contains_secret_content("API_KEY=sk-12345")

    def test_database_url_detected(self):
        assert contains_secret_content("DATABASE_URL=postgresql://user:pass@host/db")

    def test_private_key_detected(self):
        assert contains_secret_content("PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----")

    def test_neon_dsn_detected(self):
        assert contains_secret_content("NEON_DSN=postgresql://user:pass@host/db")

    def test_openai_key_detected(self):
        assert contains_secret_content("OPENAI_API_KEY=sk-proj-1234567890abcdef")

    def test_github_token_detected(self):
        assert contains_secret_content("GITHUB_TOKEN=ghp_ABCDEFGHIJKLMNOP")

    def test_normal_content_not_detected(self):
        assert not contains_secret_content("print('hello world')")

    def test_empty_string_not_detected(self):
        assert not contains_secret_content("")


class TestValidateFileContent:
    def test_secret_in_env_blocked(self, tmp_path):
        with pytest.raises(ProtectedPathError, match="secret content"):
            validate_file_content(tmp_path / ".env", "DATABASE_URL=postgresql://user:pass@host/db")

    def test_secret_in_template_blocked(self, tmp_path):
        with pytest.raises(ProtectedPathError, match="secret content"):
            validate_file_content(tmp_path / ".env.example", "API_KEY=sk-real-secret")

    def test_normal_content_allowed(self, tmp_path):
        validate_file_content(tmp_path / "config.txt", "debug=true")

    def test_placeholder_in_template_allowed(self, tmp_path):
        validate_file_content(
            tmp_path / ".env.example",
            "API_KEY=your-api-key-here",
            allow_secret_placeholders=True,
        )

    def test_secret_in_normal_file_blocked(self, tmp_path):
        with pytest.raises(ProtectedPathError, match="secret content"):
            validate_file_content(
                tmp_path / "notes.txt",
                "DATABASE_URL=postgresql://user:password@example.com/db",
            )


class TestScrubSecrets:
    def test_scrub_api_key(self):
        result = scrub_secrets("API_KEY=sk-12345-secret")
        assert "sk-12345-secret" not in result
        assert "***" in result

    def test_scrub_database_url(self):
        result = scrub_secrets("DATABASE_URL=postgresql://user:password@host/db")
        assert "password" not in result

    def test_scrub_bearer_token(self):
        result = scrub_secrets("Authorization: Bearer ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        assert "ABCDEFGHIJKLMNOPQRSTUVWXYZ" not in result

    def test_scrub_github_token(self):
        result = scrub_secrets("token: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        assert "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ" not in result

    def test_scrub_openai_key(self):
        result = scrub_secrets("OPENAI_API_KEY=sk-proj-1234567890abcdefghijklmnop")
        assert "sk-proj-1234567890abcdefghijklmnop" not in result

    def test_scrub_private_key_block(self):
        text = "-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----"
        result = scrub_secrets(text)
        assert "MIIE" not in result

    def test_scrub_no_change_for_normal(self):
        text = "print('hello')"
        assert scrub_secrets(text) == text


class TestBuildRuntimeEnv:
    def test_build_runtime_env_has_path(self):
        env = build_runtime_env()
        assert "PATH" in env

    def test_build_runtime_env_has_pythonunbuffered(self):
        env = build_runtime_env()
        assert env.get("PYTHONUNBUFFERED") == "1"

    def test_build_runtime_env_allows_valid_keys(self):
        env = build_runtime_env({"CI": "true", "NODE_ENV": "test"})
        assert env.get("CI") == "true"
        assert env.get("NODE_ENV") == "test"

    def test_build_runtime_env_rejects_invalid_keys(self):
        with pytest.raises(PermissionError, match="not allowed"):
            build_runtime_env({"LD_PRELOAD": "/tmp/evil.so"})

    def test_build_runtime_env_rejects_suspicious_keys(self):
        with pytest.raises(PermissionError, match="not allowed"):
            build_runtime_env({"BASH_ENV": "/tmp/evil.sh"})

    def test_build_runtime_env_rejects_pythonpath(self):
        with pytest.raises(PermissionError, match="not allowed"):
            build_runtime_env({"PYTHONPATH": "/tmp/evil"})


class TestWriteFileWithSecretContent:
    def test_write_file_blocks_secret_in_normal_file(self, tmp_path):
        with pytest.raises(ProtectedPathError, match="secret content"):
            write_file(
                "notes.txt",
                "DATABASE_URL=postgresql://user:password@example.com/db",
                tmp_path,
            )

    def test_write_file_allows_normal_content(self, tmp_path):
        result = write_file("notes.txt", "This is normal text", tmp_path)
        assert "Wrote" in result


class TestAuditLogNoSecrets:
    def test_secret_not_in_exception_message(self, tmp_path):
        secret = "real-super-secret-value"
        with pytest.raises(ProtectedPathError) as exc_info:
            write_file(".env", f"API_KEY={secret}", tmp_path)
        assert secret not in str(exc_info.value)


class TestPatchProtection:
    def test_patch_to_dotenv_rejected(self, tmp_path):
        patch = "--- a/.env\n+++ b/.env\n@@ -1 +1 @@\n-old\n+new"
        result = apply_patch(patch, tmp_path)
        assert "Security error" in result or "protected" in result.lower()


class TestProtectedFilesNotDeletedDuringCleanup:
    def test_existing_dotenv_not_deletable(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("SECRET=value")

        with pytest.raises(ProtectedPathError):
            delete_file(".env", tmp_path)

    def test_existing_secrets_not_deletable(self, tmp_path):
        secrets_file = tmp_path / "secrets.json"
        secrets_file.write_text('{"key": "value"}')

        with pytest.raises(ProtectedPathError):
            delete_file("secrets.json", tmp_path)
