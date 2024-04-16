import os
import toml

class Config:
    def __init__(self):
        self.config_file = "config.toml"
        self.default_config_file = "sample.config.toml"
        self.config = None

    def _load_config(self):
        if not os.path.exists(self.config_file):
            self._copy_default_config()
        try:
            with open(self.config_file, "r") as f:
                self.config = toml.load(f)
        except (OSError, toml.TomlDecodeError) as e:
            # Handle file read or parse errors gracefully
            print(f"Error loading config file: {e}")
            self.config = {}

    def _copy_default_config(self):
        try:
            with open(self.default_config_file, "r") as src, open(self.config_file, "w") as dst:
                dst.write(src.read())
        except OSError as e:
            print(f"Error copying default config: {e}")

    def _save_config(self):
        try:
            with open(self.config_file, "w") as f:
                toml.dump(self.config, f)
        except OSError as e:
            print(f"Error saving config file: {e}")

    def _get_value(self, key, default=None):
        if self.config is None:
            self._load_config()
        return self.config.get(key, default)

    def _set_value(self, key, value):
        if self.config is None:
            self._load_config()
        self.config[key] = value
        self._save_config()

    # Example of property-based access
    @property
    def bing_api_key(self):
        return self._get_value("API_KEYS.BING")

    @bing_api_key.setter
    def bing_api_key(self, key):
        self._set_value("API_KEYS.BING", key)

    # Implement other properties similarly
    # ...

    # Bulk operations
    def get_multiple_values(self, *keys):
        if self.config is None:
            self._load_config()
        return {key: self.config.get(key) for key in keys}

    def set_multiple_values(self, **kwargs):
        if self.config is None:
            self._load_config()
        self.config.update(kwargs)
        self._save_config()

    # More specific methods based on use case

    # For example, get all API keys
    def get_api_keys(self):
        return self.get_multiple_values(
            "API_KEYS.BING", 
            "API_KEYS.GOOGLE_SEARCH", 
            "API_KEYS.CLAUDE",
            # Add more keys as needed
        )

    # For example, set multiple API keys
    def set_api_keys(self, **kwargs):
        self.set_multiple_values(**kwargs)

    # Extend with methods for other groups of config keys

# Usage:
# config = Config()
# bing_key = config.bing_api_key
# config.bing_api_key = "new_key_value"
# api_keys = config.get_api_keys()
# config.set_api_keys(BING="new_bing_key", GOOGLE_SEARCH="new_google_key")
