"""
Configuration API Router

Endpoints for reading and updating server configuration.
Changes are persisted to config.yml.
"""

import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ...config import (
    get_config,
    save_config,
    reload_config,
    get_config_path,
    ServerConfig,
    DatabaseConfig,
    StorageConfig,
    FeaturesConfig,
    LibraryDefinition,
    Config
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Pydantic Models for API
# ============================================================================

class ServerConfigModel(BaseModel):
    """Server configuration model"""
    host: str = Field(..., description="Server host address")
    port: int = Field(..., ge=1, le=65535, description="Server port")
    reload: bool = Field(..., description="Auto-reload on code changes (dev only)")
    log_level: str = Field(..., description="Log level (debug, info, warning, error)")
    cors_origins: List[str] = Field(..., description="CORS allowed origins")


class DatabaseConfigModel(BaseModel):
    """Database configuration model"""
    path: Optional[str] = Field(None, description="Database path (null = auto-detect)")
    echo: bool = Field(..., description="Log all SQL queries")


class StorageConfigModel(BaseModel):
    """Storage configuration model"""
    covers_dir: Optional[str] = Field(None, description="Covers directory (null = auto-detect)")
    cache_dir: Optional[str] = Field(None, description="Cache directory")


class FeaturesConfigModel(BaseModel):
    """Features configuration model"""
    legacy_api: bool = Field(..., description="Enable YACReader-compatible legacy API")
    modern_api: bool = Field(..., description="Enable modern JSON REST API")
    reading_progress: bool = Field(..., description="Track reading progress")
    series_detection: bool = Field(..., description="Auto-detect series")
    collections: bool = Field(..., description="Enable user collections/reading lists")
    auto_thumbnails: bool = Field(..., description="Auto-generate thumbnails on scan")
    ignore_series_metadata: bool = Field(..., description="Ignore series metadata from files")


class ConfigResponseModel(BaseModel):
    """Complete configuration response"""
    server: ServerConfigModel
    database: DatabaseConfigModel
    storage: StorageConfigModel
    features: FeaturesConfigModel
    config_path: str = Field(..., description="Path to config file")


class ConfigUpdateModel(BaseModel):
    """Configuration update request"""
    server: Optional[ServerConfigModel] = None
    database: Optional[DatabaseConfigModel] = None
    storage: Optional[StorageConfigModel] = None
    features: Optional[FeaturesConfigModel] = None


# ============================================================================
# Helper Functions
# ============================================================================

def dataclass_to_dict(obj) -> Dict[str, Any]:
    """Convert dataclass to dictionary"""
    if hasattr(obj, '__dataclass_fields__'):
        return {
            key: dataclass_to_dict(value)
            for key, value in obj.__dict__.items()
        }
    elif isinstance(obj, list):
        return [dataclass_to_dict(item) for item in obj]
    else:
        return obj


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/config", response_model=ConfigResponseModel)
async def get_configuration(request: Request):
    """
    Get current server configuration

    Returns all configuration settings including server, database,
    storage, and feature flags.
    """
    try:
        config = get_config()
        config_path = get_config_path()

        return ConfigResponseModel(
            server=ServerConfigModel(**dataclass_to_dict(config.server)),
            database=DatabaseConfigModel(**dataclass_to_dict(config.database)),
            storage=StorageConfigModel(**dataclass_to_dict(config.storage)),
            features=FeaturesConfigModel(**dataclass_to_dict(config.features)),
            config_path=str(config_path)
        )
    except Exception as e:
        logger.error(f"Failed to get configuration: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get configuration: {str(e)}")


@router.put("/config")
async def update_configuration(
    update: ConfigUpdateModel,
    request: Request
):
    """
    Update server configuration

    Updates configuration and persists changes to config.yml.
    Note: Some changes (like server host/port) require a server restart.
    """
    try:
        # Get current config
        config = get_config()

        # Apply updates
        if update.server:
            config.server = ServerConfig(**update.server.model_dump())

        if update.database:
            config.database = DatabaseConfig(**update.database.model_dump())

        if update.storage:
            config.storage = StorageConfig(**update.storage.model_dump())

        if update.features:
            config.features = FeaturesConfig(**update.features.model_dump())

        # Save to file
        save_config(config)

        # Reload configuration
        reload_config()

        logger.info("Configuration updated successfully")

        return {
            "success": True,
            "message": "Configuration updated successfully",
            "restart_required": update.server is not None,
            "config_path": str(get_config_path())
        }

    except Exception as e:
        logger.error(f"Failed to update configuration: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {str(e)}")


@router.get("/config/path")
async def get_config_file_path():
    """
    Get the path to the configuration file

    Returns the absolute path to the config.yml file being used.
    """
    return {
        "config_path": str(get_config_path()),
        "exists": get_config_path().exists()
    }


@router.post("/config/reload")
async def reload_configuration():
    """
    Reload configuration from file

    Reloads the configuration from config.yml without restarting the server.
    Some settings (like server host/port) require a restart to take effect.
    """
    try:
        reload_config()
        logger.info("Configuration reloaded from file")

        return {
            "success": True,
            "message": "Configuration reloaded successfully",
            "config_path": str(get_config_path())
        }
    except Exception as e:
        logger.error(f"Failed to reload configuration: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reload configuration: {str(e)}")
