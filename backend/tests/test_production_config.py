"""Unit tests for fail-closed production runtime configuration."""
import pytest

import server


def _valid_production_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUDITPRO_ADMIN_USERNAME", "finance-admin")
    monkeypatch.setenv("AUDITPRO_ADMIN_PASSWORD", "a-strong-test-password-123")
    monkeypatch.setenv("AUDITPRO_SESSION_SECRET", "x" * 48)
    monkeypatch.setenv("COOKIE_SECURE", "true")
    monkeypatch.setenv("AUDITPRO_TEST_OCR", "false")
    monkeypatch.setenv("EMERGENT_LLM_KEY", "test-only-placeholder")
    monkeypatch.setenv("MONGO_URL", "mongodb+srv://example.invalid/auditpro?retryWrites=true")
    monkeypatch.setattr(server, "cors_origins", ["https://finance.example.com"])


def test_production_configuration_accepts_secure_shape(monkeypatch):
    _valid_production_env(monkeypatch)
    server.validate_runtime_configuration()


@pytest.mark.parametrize(
    ("name", "value", "message"),
    [
        ("AUDITPRO_ADMIN_USERNAME", "auditpro-admin", "non-default"),
        ("COOKIE_SECURE", "false", "COOKIE_SECURE=true"),
        ("AUDITPRO_TEST_OCR", "true", "forbidden"),
        ("EMERGENT_LLM_KEY", "", "EMERGENT_LLM_KEY"),
        ("MONGO_URL", "mongodb://mongo:27017/auditpro", "TLS"),
    ],
)
def test_production_configuration_rejects_unsafe_settings(monkeypatch, name, value, message):
    _valid_production_env(monkeypatch)
    monkeypatch.setenv(name, value)
    with pytest.raises(RuntimeError, match=message):
        server.validate_runtime_configuration()


def test_production_configuration_rejects_local_cors(monkeypatch):
    _valid_production_env(monkeypatch)
    monkeypatch.setattr(server, "cors_origins", ["https://finance.example.com", "http://localhost:3000"])
    with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
        server.validate_runtime_configuration()


def test_development_configuration_keeps_local_defaults(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    server.validate_runtime_configuration()
