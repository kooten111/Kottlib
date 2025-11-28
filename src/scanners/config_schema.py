"""
Configuration schema types for declarative scanner configuration.

This module provides types for defining rich, metadata-driven configuration
options that scanners can declare. The WebUI uses these schemas to automatically
render appropriate input controls.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Any, List, Optional


class ConfigType(str, Enum):
    """Types of configuration options that determine how they're rendered in the UI"""
    STRING = "string"           # Plain text input
    SECRET = "secret"           # Password field with show/hide toggle
    INTEGER = "integer"         # Number input (whole numbers)
    FLOAT = "float"             # Number input or slider (decimals)
    BOOLEAN = "boolean"         # Toggle switch
    SELECT = "select"           # Dropdown (single choice)
    MULTI_SELECT = "multi_select"  # Checkboxes (multiple choices)


@dataclass
class ConfigOption:
    """
    Declarative configuration option with rich metadata.

    This class defines a single configuration option that a scanner needs,
    including type information, validation rules, UI hints, and descriptions.

    Attributes:
        key: Unique identifier for this config option (used in storage)
        type: The type of configuration (determines UI rendering)
        label: Human-readable label shown in the UI
        description: Help text explaining what this option does
        required: Whether this option must be provided
        default: Default value if not specified
        advanced: Whether to show this in an "Advanced" section
        min_value: Minimum value (for INTEGER/FLOAT)
        max_value: Maximum value (for INTEGER/FLOAT)
        step: Step increment for sliders (for FLOAT)
        options: Available choices (for SELECT/MULTI_SELECT)
        placeholder: Placeholder text for input fields
        validation_pattern: Regex pattern for validation (for STRING)
        validation_message: Message to show if validation fails
    """
    key: str
    type: ConfigType
    label: str
    description: str = ""
    required: bool = False
    default: Optional[Any] = None
    advanced: bool = False

    # Numeric constraints (INTEGER/FLOAT)
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    step: Optional[float] = None

    # Choice constraints (SELECT/MULTI_SELECT)
    options: Optional[List[Any]] = None

    # String constraints
    placeholder: Optional[str] = None
    validation_pattern: Optional[str] = None
    validation_message: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        result = {
            "key": self.key,
            "type": self.type.value,
            "label": self.label,
            "description": self.description,
            "required": self.required,
            "default": self.default,
            "advanced": self.advanced,
        }

        # Add optional fields only if set
        if self.min_value is not None:
            result["min_value"] = self.min_value
        if self.max_value is not None:
            result["max_value"] = self.max_value
        if self.step is not None:
            result["step"] = self.step
        if self.options is not None:
            result["options"] = self.options
        if self.placeholder is not None:
            result["placeholder"] = self.placeholder
        if self.validation_pattern is not None:
            result["validation_pattern"] = self.validation_pattern
        if self.validation_message is not None:
            result["validation_message"] = self.validation_message

        return result
