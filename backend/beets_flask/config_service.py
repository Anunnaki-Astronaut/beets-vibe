import shutil
from pathlib import Path
from typing import Any, Dict, List

import yaml

from beets_flask.config import get_config

SUPPORTED_METADATA_PLUGINS = [
    "discogs",
    "spotify",
    "musicbrainz",
]


class ConfigService:
    def __init__(self, config=None):
        self.config = config or get_config()
        self.beets_config_path: Path = Path(self.config.get_beets_config_path())

    def get_metadata_plugins_config(self) -> Dict[str, Any]:
        """
        Reads the beets config and returns a dictionary of supported metadata plugins
        and their configurations. Redacts sensitive fields.
        """
        config_data = self._read_config_yaml()
        enabled_plugins = config_data.get("plugins", [])
        
        plugins_config = {}
        for plugin in SUPPORTED_METADATA_PLUGINS:
            is_enabled = plugin in enabled_plugins
            plugin_settings = config_data.get(plugin, {})

            # Redact sensitive fields
            redacted_settings = {}
            for key, value in plugin_settings.items():
                if "token" in key or "secret" in key or "key" in key:
                    redacted_settings[key] = "********"
                else:
                    redacted_settings[key] = value
            
            plugins_config[plugin] = {
                "enabled": is_enabled,
                "settings": redacted_settings,
            }
        return plugins_config

    def update_metadata_plugin_config(self, plugin_name: str, settings: Dict[str, Any], enabled: bool):
        """
        Updates the configuration for a specific metadata plugin.
        """
        if plugin_name not in SUPPORTED_METADATA_PLUGINS:
            raise ValueError(f"Plugin {plugin_name} is not supported for configuration.")

        config_data = self._read_config_yaml()

        # Update enabled status
        enabled_plugins: List[str] = config_data.get("plugins", [])
        if enabled and plugin_name not in enabled_plugins:
            enabled_plugins.append(plugin_name)
        elif not enabled and plugin_name in enabled_plugins:
            enabled_plugins.remove(plugin_name)
        config_data["plugins"] = enabled_plugins

        # Update plugin-specific settings
        if plugin_name not in config_data:
            config_data[plugin_name] = {}
        
        # Only update settings that are not redacted
        for key, value in settings.items():
            if value != "********":
                config_data[plugin_name][key] = value

        self._write_config_yaml(config_data)

    def _backup_config(self):
        """Creates a backup of the config file."""
        backup_path = self.beets_config_path.with_suffix(".yaml.bak")
        shutil.copy(self.beets_config_path, backup_path)

    def _read_config_yaml(self) -> Dict[str, Any]:
        """Reads the raw YAML config file."""
        with open(self.beets_config_path, "r") as f:
            return yaml.safe_load(f)

    def _write_config_yaml(self, data: Dict[str, Any]):
        """Writes data to the YAML config file."""
        self._backup_config()
        with open(self.beets_config_path, "w") as f:
            yaml.dump(data, f, sort_keys=False)
