import pytest

from app.config import _as_bool, _load_config_file, _setting


def test_loads_configuration_file(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("auth_enabled: false\n", encoding="utf-8")

    assert _load_config_file(str(config_file)) == {"auth_enabled": False}


def test_invalid_configuration_file_is_reported(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("invalid: [", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Invalid YAML"):
        _load_config_file(str(config_file))


def test_configuration_file_must_contain_mapping(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("- one\n- two\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="YAML mapping"):
        _load_config_file(str(config_file))


def test_environment_overrides_configuration_file(monkeypatch):
    monkeypatch.setattr("app.config.FILE_CONFIG", {"auth_enabled": False})
    monkeypatch.setenv("FEATURE_AUTH_REQUIRED", "true")

    assert _as_bool(_setting("auth_enabled", "FEATURE_AUTH_REQUIRED", False)) is True


@pytest.mark.parametrize(("value", "expected"), [
    ("true", True),
    ("YES", True),
    ("0", False),
    ("off", False),
])
def test_boolean_configuration_values(value, expected):
    assert _as_bool(value) is expected


def test_invalid_boolean_configuration_is_reported():
    with pytest.raises(ValueError, match="Expected a boolean"):
        _as_bool("sometimes")
