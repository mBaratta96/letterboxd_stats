import getpass
import os
import platformdirs
import tomli
from decouple import config as env_config, UndefinedValueError

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
        print(
            f"No config file found at {file_path}. "
            + "Please add a config.toml in that folder or specify a custom one with the -c command."
        )
        user_config = {}

    # MApply defaults
    merged_config = _merge_dicts(CONFIG_DEFAULTS, user_config)

    # Override with environment variables if available
    merged_config = _apply_env_variables(merged_config, ENV_CONFIG_MAPPING)

    _config_cache = merged_config  # Cache the config

    return merged_config

def _merge_dicts(defaults, overrides):
    """Recursively merge two dictionaries."""
    merged = defaults.copy()
    for key, value in overrides.items():
        if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
            merged[key] = _merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged

def _apply_env_variables(config, env_config_mapping):
    """
    Override config with environment variables using python-decouple.
    
    Args:
        config (dict): Existing configuration.
        env_config_mapping (dict): Mapping of environment variables to config keys.
        
    Returns:
        dict: Updated configuration.
    """
    for env_var, (section, key) in env_config_mapping.items():
        try:
            value = env_config(env_var)
            # Handle type conversions
            if isinstance(config[section][key], bool):
                value = value.lower() == "true"
            elif isinstance(config[section][key], int):
                value = int(value)
            config[section][key] = value
        except UndefinedValueError:
            # Skip if the environment variable is not set
            pass
    return config
