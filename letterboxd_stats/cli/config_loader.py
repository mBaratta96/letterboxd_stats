"""
Configuration Loader Module
===========================

This module provides functionality to load and manage configuration settings
for the Letterboxd Stats application. It supports hierarchical configuration
merging from default settings, user-provided TOML files, and environment variables.

Features:
---------
1. **Default Configuration**:
   - Provides a default config directory.
   - Contains pre-defined default settings for the application in `CONFIG_DEFAULTS`.

2. **TOML Configuration File Support**:
   - Loads user-specific settings from a TOML file (default path: `{user_config_dir}/config.toml`).

3. **Environment Variable Overrides**:
   - Overrides configuration values with environment variables defined in `ENV_CONFIG_MAPPING`.

"""

import getpass
import logging
import os

import platformdirs
import tomli
from decouple import UndefinedValueError
from decouple import config as env_config

logger = logging.getLogger(__name__)

default_config_dir = platformdirs.user_config_dir("letterboxd_stats", getpass.getuser())

CONFIG_DEFAULTS = {
    "CLI": {
        "poster_columns": 80,
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


def load_config(file_path=None):
    """Load config from a file and merge with defaults and environment variables."""
    logger.info("Loading configuration...")
    # Determine the config path
    file_path = file_path or os.path.join(default_config_dir, "config.toml")
    logger.debug("Configuration file path: %s", file_path)

    # Load the TOML file if it exists
    if os.path.exists(file_path):
        logger.info("Found configuration file at %s", file_path)
        with open(file_path, "rb") as f:
            try:
                user_config = tomli.load(f)
                logger.info("Configuration file passed validation check.")
            except Exception as e:
                logger.error("Failed to parse configuration file: %s", e)
                raise
    else:
        logger.warning(
            "No config file found at %s. Please add a config.toml in that \
                folder or specify a custom one with the -c command.",
            file_path,
        )
        user_config = {}

    # Apply defaults
    logger.info("Applying defaults where no values provided.")

    merged_config = _merge_dicts(CONFIG_DEFAULTS, user_config)
    logger.debug("Merged configuration with defaults: %s", merged_config)

    # Override with environment variables if available
    merged_config = _apply_env_variables(merged_config, ENV_CONFIG_MAPPING)

    logger.info("Configuration loading complete.")
    return merged_config


def _merge_dicts(defaults, overrides):
    """Recursively merge two dictionaries."""
    merged = defaults.copy()
    for key, value in overrides.items():
        if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
            merged[key] = _merge_dicts(merged[key], value)
        else:
            merged[key] = value

    logger.debug("Merged configuration: %s", merged)
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
    logger.info("Applying environment variable overrides...")
    for env_var, (section, key) in env_config_mapping.items():
        try:
            value = env_config(env_var)
            # Handle type conversions
            if isinstance(config[section][key], bool):
                value = value.lower() == "true"
            elif isinstance(config[section][key], int):
                value = int(value)
            config[section][key] = value
            logger.info(
                "Overrode %s.%s with environment variable %s", section, key, env_var
            )
        except UndefinedValueError:
            logger.debug("Environment variable %s not set. Skipping.", env_var)
    logger.debug("Configuration after environment variable overrides: %s", config)
    return config
