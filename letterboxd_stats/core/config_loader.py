import getpass
import os
import platformdirs
import tomli

default_config_dir = platformdirs.user_config_dir("letterboxd_stats", getpass.getuser())

CONFIG_DEFAULTS = {
    "CLI": {
        "poster_columns": 180,
        "ascending": False,
    },
    "TMDB": {
        "get_list_runtimes": False,
    },
}

ENV_CONFIG_MAPPING = {
    "LBSTATS_CLI_POSTER_COLUMNS": ("CLI", "poster_columns"),
    "LBSTATS_CLI_ASCENDING": ("CLI", "ascending"),
    "LBSTATS_TMDB_GET_LIST_RUNTIMES": ("TMDB", "get_list_runtimes"),
    "LBSTATS_TMDB_API_KEY": ("TMDB", "api_key"),
    "LBSTATS_USERNAME": ("Letterboxd", "username"),
    "LBSTATS_PASSWORD": ("Letterboxd", "password"),
}

_config_cache = None  # Private variable to store the loaded configuration

def load_config(file_path=None):
    """Load config from a file and merge with defaults and environment variables."""
    global _config_cache
    if _config_cache is not None:
        return _config_cache  # Return cached config if already loaded
    
    # Determine the config path
    file_path = file_path or os.path.join(default_config_dir, "config.toml")

    # Load the TOML file if it exists
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            user_config = tomli.load(f)
    else:
        user_config = {}

    # Merge user_config with defaults
    merged_config = merge_dicts(CONFIG_DEFAULTS, user_config)

    # Override with environment variables if available
    merged_config = apply_env_variables(merged_config, ENV_CONFIG_MAPPING)

    _config_cache = merged_config  # Cache the config

    return merged_config

def merge_dicts(defaults, overrides):
    """Recursively merge two dictionaries."""
    merged = defaults.copy()
    for key, value in overrides.items():
        if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
            merged[key] = merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged

def apply_env_variables(config, env_config_mapping):
    """Override config with environment variables."""
    for env_var, keys in env_config_mapping.items():
        if env_var in os.environ:
            section, key = keys
            value = os.environ[env_var]
            # Convert boolean strings to actual booleans
            if value.lower() in ["true", "false"]:
                value = value.lower() == "true"
            elif value.isdigit():
                value = int(value)
            config[section][key] = value
    return config
