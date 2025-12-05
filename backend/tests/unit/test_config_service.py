# backend/tests/unit/test_config_service.py

from copy import deepcopy
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

import pytest
from ruamel.yaml import YAML

from beets_flask.config_service import ConfigService, SUPPORTED_METADATA_PLUGINS


@pytest.fixture
def mock_config_data():
    """Base beets config used by the ConfigService tests."""
    return {
        "plugins": ["discogs", "musicbrainz", "keyfinder"],
        "discogs": {
            "token": "test_token",
            "secret": "test_secret",
            "user_agent": "test_agent",
        },
        "spotify": {
            "api_key": "test_api_key",
        },
        "musicbrainz": {},
        "autobpm": {"max_tempo": "200"},
        "keyfinder": {},
    }


@pytest.fixture
def config_service(mock_config_data):
    """
    Create a ConfigService instance that works entirely in memory.

    - _read_config_yaml returns a fresh copy of mock_config_data.
    - _write_config_yaml stores the last written config in `written["data"]`.
    - _backup_config is stubbed out (no filesystem access).
    """
    service = ConfigService.__new__(ConfigService)
    service.beets_config_path = Path("/fake/config.yaml")

    written = {}

    def fake_read():
        return deepcopy(mock_config_data)

    def fake_write(data):
        written["data"] = deepcopy(data)

    service._read_config_yaml = fake_read
    service._write_config_yaml = fake_write
    service._backup_config = lambda: None  # no real filesystem work

    return service, written


def test_get_metadata_plugins_config(config_service, mock_config_data):
    service, _ = config_service

    plugins_config = service.get_metadata_plugins_config()

    # Discogs: enabled, secrets redacted, non-secret preserved
    assert plugins_config["discogs"]["enabled"] is True
    discogs_settings = plugins_config["discogs"]["settings"]
    assert discogs_settings["token"] == "********"
    assert discogs_settings["secret"] == "********"
    assert discogs_settings["user_agent"] == "test_agent"

    # Spotify: not in plugins list, so disabled; api_key is treated as secret
    assert plugins_config["spotify"]["enabled"] is False
    assert plugins_config["spotify"]["settings"]["api_key"] == "********"

    # MusicBrainz: enabled (in plugins list), no extra settings
    assert plugins_config["musicbrainz"]["enabled"] is True
    assert plugins_config["musicbrainz"]["settings"] == {}

    # Autobpm: not enabled, but settings are present
    assert plugins_config["autobpm"]["enabled"] is False
    assert plugins_config["autobpm"]["settings"] == {"max_tempo": "200"}

    # Keyfinder: enabled, no settings
    assert plugins_config["keyfinder"]["enabled"] is True
    assert plugins_config["keyfinder"]["settings"] == {}

    # Beatport and others: not in config, so disabled and no settings
    assert plugins_config["beatport"]["enabled"] is False
    assert plugins_config["beatport"]["settings"] == {}
    assert plugins_config["lyrics"]["enabled"] is False
    assert plugins_config["replaygain"]["enabled"] is False


def test_update_metadata_plugin_config_enable(config_service):
    service, written = config_service

    service.update_metadata_plugin_config(
        "spotify", {"api_key": "new_key"}, enabled=True
    )

    data = written["data"]

    # Spotify should be in the plugins list and have updated api_key
    assert "spotify" in data["plugins"]
    assert data["spotify"]["api_key"] == "new_key"


def test_update_metadata_plugin_config_disable(config_service):
    service, written = config_service

    service.update_metadata_plugin_config("discogs", {}, enabled=False)

    data = written["data"]

    # Discogs should be removed from plugins list
    assert "discogs" not in data["plugins"]


def test_backup_created_on_update(mock_config_data):
    """
    For backup behavior we call the real _write_config_yaml but stub out
    shutil.copy and open so nothing touches the real filesystem.
    """
    service = ConfigService.__new__(ConfigService)
    service.beets_config_path = Path("/fake/config.yaml")

    # Use in-memory config for reads
    service._read_config_yaml = lambda: deepcopy(mock_config_data)

    with patch("beets_flask.config_service.shutil.copy") as m_copy, \
         patch("ruamel.yaml.YAML.dump") as m_dump, \
         patch("builtins.open", mock_open()):
        service.update_metadata_plugin_config(
            "spotify", {"api_key": "new_key"}, enabled=True
        )

        backup_path = service.beets_config_path.with_suffix(".yaml.bak")
        m_copy.assert_called_once_with(service.beets_config_path, backup_path)
        m_dump.assert_called_once()