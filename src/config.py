"""
Configuration Management

Handles MINIMAL bootstrap configuration including:
- Server settings (host, port, log_level, cors_origins)
- Database settings (path only)

All other settings (storage, features, libraries) are stored in the database.

Configuration is loaded from:
1. config.yml (bootstrap settings only)
2. Environment variables (override)
3. Defaults (fallback)
"""

import os
import yaml
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field, asdict
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration Data Classes
# ============================================================================

@dataclass
class ServerConfig:
    """Server configuration"""
    host: str = "0.0.0.0"
    port: int = 8081
    reload: bool = False
    log_level: str = "info"
    cors_origins: List[str] = field(default_factory=lambda: ["*"])


@dataclass
class DatabaseConfig:
    """Database configuration (bootstrap only)"""
    path: Optional[str] = None  # None = auto-detect platform default
    echo: bool = False  # Log all SQL queries (debugging)


# ============================================================================
# Main Configuration
# ============================================================================

@dataclass
class Config:
    """Main bootstrap configuration (server + database only)"""
    server: ServerConfig = field(default_factory=ServerConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)


# ============================================================================
# Configuration File Management
# ============================================================================

def get_config_path() -> Path:
    """
    Get configuration file path

    Looks for config.yml in:
    1. Current directory
    2. User config directory (~/.config/yaclib/)
    3. System config directory (/etc/yaclib/)
    """
    # Check current directory first
    local_config = Path("config.yml")
    if local_config.exists():
        return local_config

    # Check user config directory
    from .utils.platform import get_config_dir
    import platform
    
    user_config_dir = get_config_dir()

    user_config = user_config_dir / 'config.yml'
    if user_config.exists():
        return user_config

    # Check system config (Linux only)
    if platform.system() == 'Linux':
        system_config = Path('/etc/yaclib/config.yml')
        if system_config.exists():
            return system_config

    # Return user config path (even if it doesn't exist yet)
    return user_config


def create_default_config() -> Config:
    """Create default bootstrap configuration"""
    return Config(
        server=ServerConfig(),
        database=DatabaseConfig()
    )


def load_config(config_path: Optional[Path] = None) -> Config:
    """
    Load bootstrap configuration from file

    Args:
        config_path: Path to config file (None = auto-detect)

    Returns:
        Config object with bootstrap settings (server + database only)
    """
    if config_path is None:
        config_path = get_config_path()

    # Start with defaults
    config = create_default_config()

    # Load from file if it exists
    if config_path.exists():
        logger.info(f"Loading config from: {config_path}")
        try:
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f)

            if not data:
                logger.warning("Config file is empty, using defaults")
                return config

            # Parse ONLY bootstrap sections (server and database)
            if 'server' in data:
                config.server = ServerConfig(**data['server'])

            if 'database' in data:
                config.database = DatabaseConfig(**data['database'])

            # Ignore other sections - they should be in database
            ignored_sections = []
            for section in ['storage', 'features', 'libraries']:
                if section in data:
                    ignored_sections.append(section)
            
            if ignored_sections:
                logger.warning(
                    f"Ignoring sections from config file (should be in database): {', '.join(ignored_sections)}"
                )

        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            logger.warning("Using default configuration")

    else:
        logger.info(f"No config file found at {config_path}, creating default config")
        # Create default config file
        try:
            save_config(config, config_path)
            logger.info(f"Created default config at: {config_path}")
        except Exception as e:
            logger.warning(f"Failed to create default config: {e}")
            logger.info("Continuing with in-memory defaults")

    # Apply environment variable overrides
    config = apply_env_overrides(config)

    return config


# Environment variable override mapping
# Format: 'ENV_VAR': ('section', 'field', converter_function)
ENV_OVERRIDES = {
    'KOTTLIB_HOST': ('server', 'host', str),
    'KOTTLIB_PORT': ('server', 'port', int),
    'KOTTLIB_DB_PATH': ('database', 'path', str),
    'KOTTLIB_LOG_LEVEL': ('server', 'log_level', str),
}


def apply_env_overrides(config: Config) -> Config:
    """
    Apply environment variable overrides using a mapping pattern.

    Environment variables:
    - KOTTLIB_HOST
    - KOTTLIB_PORT
    - KOTTLIB_DB_PATH
    - KOTTLIB_LOG_LEVEL
    """
    for env_var, (section, field, converter) in ENV_OVERRIDES.items():
        value = os.getenv(env_var)
        if value:
            try:
                setattr(getattr(config, section), field, converter(value))
            except (ValueError, AttributeError) as e:
                logger.warning(f"Invalid {env_var}: {value} - {e}")
    
    return config


def save_config(config: Config, config_path: Optional[Path] = None):
    """
    Save bootstrap configuration to file

    Args:
        config: Bootstrap configuration to save (server + database only)
        config_path: Path to save to (None = auto-detect)
    """
    if config_path is None:
        config_path = get_config_path()

    # Create directory if needed
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dict - ONLY server and database
    data = {
        'server': asdict(config.server),
        'database': asdict(config.database)
    }

    # Save to file
    with open(config_path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    logger.info(f"Configuration saved to: {config_path}")


# ============================================================================
# Global Configuration
# ============================================================================

# Global config instance (loaded on import)
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global configuration (lazy loaded)"""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config():
    """Reload configuration from file"""
    global _config
    _config = load_config()
    logger.info("Configuration reloaded")
