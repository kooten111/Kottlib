"""
Configuration Management

Handles server configuration including:
- Server settings (host, port, etc.)
- Library definitions
- Feature flags
- Storage locations

Configuration is loaded from:
1. config.yml (user configuration)
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
    """Database configuration"""
    path: Optional[str] = None  # None = auto-detect platform default
    echo: bool = False  # Log SQL queries


@dataclass
class StorageConfig:
    """Storage paths configuration"""
    covers_dir: Optional[str] = None  # None = auto-detect (next to database)
    cache_dir: Optional[str] = None   # For temporary page cache


@dataclass
class LibraryDefinition:
    """Library definition from config"""
    name: str
    path: str
    auto_scan: bool = True
    scan_on_startup: bool = False
    settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FeaturesConfig:
    """Feature flags"""
    legacy_api: bool = True
    modern_api: bool = True
    reading_progress: bool = True
    series_detection: bool = True
    collections: bool = True
    auto_thumbnails: bool = True


@dataclass
class Config:
    """Main configuration"""
    server: ServerConfig = field(default_factory=ServerConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    features: FeaturesConfig = field(default_factory=FeaturesConfig)
    libraries: List[LibraryDefinition] = field(default_factory=list)


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
    import platform
    system = platform.system()

    if system == 'Linux':
        user_config_dir = Path.home() / '.config' / 'yaclib'
    elif system == 'Darwin':  # macOS
        user_config_dir = Path.home() / 'Library' / 'Application Support' / 'YACLib'
    elif system == 'Windows':
        user_config_dir = Path(os.environ.get('APPDATA', Path.home())) / 'YACLib'
    else:
        user_config_dir = Path.home() / '.yaclib'

    user_config = user_config_dir / 'config.yml'
    if user_config.exists():
        return user_config

    # Check system config (Linux only)
    if system == 'Linux':
        system_config = Path('/etc/yaclib/config.yml')
        if system_config.exists():
            return system_config

    # Return user config path (even if it doesn't exist yet)
    return user_config


def create_default_config() -> Config:
    """Create default configuration"""
    return Config(
        server=ServerConfig(),
        database=DatabaseConfig(),
        storage=StorageConfig(),
        features=FeaturesConfig(),
        libraries=[]
    )


def load_config(config_path: Optional[Path] = None) -> Config:
    """
    Load configuration from file

    Args:
        config_path: Path to config file (None = auto-detect)

    Returns:
        Config object with settings
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

            # Parse sections
            if 'server' in data:
                config.server = ServerConfig(**data['server'])

            if 'database' in data:
                config.database = DatabaseConfig(**data['database'])

            if 'storage' in data:
                config.storage = StorageConfig(**data['storage'])

            if 'features' in data:
                config.features = FeaturesConfig(**data['features'])

            if 'libraries' in data:
                config.libraries = [
                    LibraryDefinition(**lib) for lib in data['libraries']
                ]

            logger.info(f"Loaded {len(config.libraries)} libraries from config")

        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            logger.warning("Using default configuration")

    else:
        logger.info(f"No config file found at {config_path}, using defaults")

    # Apply environment variable overrides
    config = apply_env_overrides(config)

    return config


def apply_env_overrides(config: Config) -> Config:
    """
    Apply environment variable overrides

    Environment variables:
    - YACLIB_HOST
    - YACLIB_PORT
    - YACLIB_DB_PATH
    - YACLIB_LOG_LEVEL
    """
    if os.getenv('YACLIB_HOST'):
        config.server.host = os.getenv('YACLIB_HOST')

    if os.getenv('YACLIB_PORT'):
        try:
            config.server.port = int(os.getenv('YACLIB_PORT'))
        except ValueError:
            logger.warning(f"Invalid YACLIB_PORT: {os.getenv('YACLIB_PORT')}")

    if os.getenv('YACLIB_DB_PATH'):
        config.database.path = os.getenv('YACLIB_DB_PATH')

    if os.getenv('YACLIB_LOG_LEVEL'):
        config.server.log_level = os.getenv('YACLIB_LOG_LEVEL')

    return config


def save_config(config: Config, config_path: Optional[Path] = None):
    """
    Save configuration to file

    Args:
        config: Configuration to save
        config_path: Path to save to (None = auto-detect)
    """
    if config_path is None:
        config_path = get_config_path()

    # Create directory if needed
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dict
    data = {
        'server': asdict(config.server),
        'database': asdict(config.database),
        'storage': asdict(config.storage),
        'features': asdict(config.features),
        'libraries': [asdict(lib) for lib in config.libraries]
    }

    # Save to file
    with open(config_path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    logger.info(f"Configuration saved to: {config_path}")


def create_example_config(output_path: Path):
    """
    Create an example configuration file

    Args:
        output_path: Where to save the example config
    """
    config = Config(
        server=ServerConfig(
            host="0.0.0.0",
            port=8081,
            reload=False,
            log_level="info",
            cors_origins=["*"]
        ),
        database=DatabaseConfig(
            path=None,  # Auto-detect
            echo=False
        ),
        storage=StorageConfig(
            covers_dir=None,  # Auto-detect
            cache_dir=None
        ),
        features=FeaturesConfig(
            legacy_api=True,
            modern_api=True,
            reading_progress=True,
            series_detection=True,
            collections=True,
            auto_thumbnails=True
        ),
        libraries=[
            LibraryDefinition(
                name="Comics",
                path="/path/to/comics",
                auto_scan=True,
                scan_on_startup=False,
                settings={
                    "sort_mode": "folders_first",
                    "default_reading_direction": "ltr"
                }
            ),
            LibraryDefinition(
                name="Manga",
                path="/path/to/manga",
                auto_scan=True,
                scan_on_startup=False,
                settings={
                    "sort_mode": "folders_first",
                    "default_reading_direction": "rtl"
                }
            )
        ]
    )

    save_config(config, output_path)
    logger.info(f"Example config created at: {output_path}")


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
