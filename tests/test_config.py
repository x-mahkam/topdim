import pytest

from topdim.config import ConfigError, load_config, parse_admin_ids


def test_parse_admin_ids():
    assert parse_admin_ids("1, 2;3,,") == frozenset({1, 2, 3})
    assert parse_admin_ids("") == frozenset()
    with pytest.raises(ConfigError):
        parse_admin_ids("12, abc")


def test_load_config_requires_token(monkeypatch):
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    with pytest.raises(ConfigError):
        load_config(env_file=None)


def test_load_config_reads_env(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "123:abc")
    monkeypatch.setenv("ADMIN_IDS", "5")
    monkeypatch.delenv("DB_PATH", raising=False)
    config = load_config(env_file=None)
    assert config.bot_token == "123:abc"
    assert config.admin_ids == {5}
    assert config.db_path == "topdim.db"
