"""Centralized configuration management for cloud-resource-inefficiency."""

import os
from dataclasses import dataclass, field
from typing import Optional

import yaml


@dataclass
class ScanConfig:
    """
    Configuration for scan operations.

    Supports loading from environment variables (prefix: CRI_) and YAML files.
    """

    # Scan parameters
    lookback_days: int = 14
    max_allowed_io_ops: float = 0.0
    timeout_seconds: int = 300

    # Retry configuration
    retry_max_attempts: int = 3
    retry_base_delay_seconds: float = 1.0
    retry_backoff_factor: float = 2.0
    retry_max_delay_seconds: float = 32.0

    # Circuit breaker configuration
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout_seconds: float = 60.0

    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None

    # Regions to scan
    regions: list = field(default_factory=lambda: ["us-east-1"])

    # Resource types to scan (empty list = all)
    resource_types: list = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "ScanConfig":
        """
        Load configuration from environment variables.

        Environment variables use CRI_ prefix, e.g., CRI_LOOKBACK_DAYS=30
        """
        config_dict = {
            "lookback_days": int(os.getenv("CRI_LOOKBACK_DAYS", "14")),
            "max_allowed_io_ops": float(os.getenv("CRI_MAX_ALLOWED_IO_OPS", "0.0")),
            "timeout_seconds": int(os.getenv("CRI_TIMEOUT_SECONDS", "300")),
            "retry_max_attempts": int(os.getenv("CRI_RETRY_MAX_ATTEMPTS", "3")),
            "retry_base_delay_seconds": float(os.getenv("CRI_RETRY_BASE_DELAY_SECONDS", "1.0")),
            "retry_backoff_factor": float(os.getenv("CRI_RETRY_BACKOFF_FACTOR", "2.0")),
            "retry_max_delay_seconds": float(os.getenv("CRI_RETRY_MAX_DELAY_SECONDS", "32.0")),
            "circuit_breaker_failure_threshold": int(
                os.getenv("CRI_CIRCUIT_BREAKER_FAILURE_THRESHOLD", "5")
            ),
            "circuit_breaker_recovery_timeout_seconds": float(
                os.getenv("CRI_CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS", "60.0")
            ),
            "log_level": os.getenv("CRI_LOG_LEVEL", "INFO"),
            "log_file": os.getenv("CRI_LOG_FILE"),
        }

        # Parse regions (comma-separated)
        regions_str = os.getenv("CRI_REGIONS", "us-east-1")
        config_dict["regions"] = [r.strip() for r in regions_str.split(",")]

        # Parse resource types (comma-separated)
        resource_types_str = os.getenv("CRI_RESOURCE_TYPES", "")
        config_dict["resource_types"] = (
            [r.strip() for r in resource_types_str.split(",") if r.strip()] if resource_types_str else []
        )

        return cls(**config_dict)

    @classmethod
    def from_yaml_file(cls, filepath: str) -> "ScanConfig":
        """
        Load configuration from a YAML file.

        Example YAML structure:
        ```yaml
        lookback_days: 30
        max_allowed_io_ops: 100.0
        timeout_seconds: 600
        log_level: DEBUG
        regions:
          - us-east-1
          - us-west-2
        ```
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Configuration file not found: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f) or {}

        # Merge with defaults
        return cls(**config_dict)

    @classmethod
    def from_yaml_file_optional(cls, filepath: Optional[str] = None) -> "ScanConfig":
        """
        Load configuration from YAML file if specified, otherwise use environment.

        Args:
            filepath: Path to YAML config file. If None, loads from environment.

        Returns:
            ScanConfig instance.
        """
        if filepath:
            return cls.from_yaml_file(filepath)
        return cls.from_env()

    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            "lookback_days": self.lookback_days,
            "max_allowed_io_ops": self.max_allowed_io_ops,
            "timeout_seconds": self.timeout_seconds,
            "retry_max_attempts": self.retry_max_attempts,
            "retry_base_delay_seconds": self.retry_base_delay_seconds,
            "retry_backoff_factor": self.retry_backoff_factor,
            "retry_max_delay_seconds": self.retry_max_delay_seconds,
            "circuit_breaker_failure_threshold": self.circuit_breaker_failure_threshold,
            "circuit_breaker_recovery_timeout_seconds": self.circuit_breaker_recovery_timeout_seconds,
            "log_level": self.log_level,
            "log_file": self.log_file,
            "regions": self.regions,
            "resource_types": self.resource_types,
        }

    def validate(self) -> bool:
        """
        Validate configuration values.

        Returns:
            True if valid, False otherwise.
        """
        if self.lookback_days < 1:
            raise ValueError("lookback_days must be >= 1")
        if self.timeout_seconds < 1:
            raise ValueError("timeout_seconds must be >= 1")
        if self.retry_max_attempts < 1:
            raise ValueError("retry_max_attempts must be >= 1")
        if self.retry_base_delay_seconds < 0:
            raise ValueError("retry_base_delay_seconds must be >= 0")
        if self.retry_backoff_factor < 1.0:
            raise ValueError("retry_backoff_factor must be >= 1.0")
        if self.circuit_breaker_failure_threshold < 1:
            raise ValueError("circuit_breaker_failure_threshold must be >= 1")
        if self.circuit_breaker_recovery_timeout_seconds < 0:
            raise ValueError("circuit_breaker_recovery_timeout_seconds must be >= 0")
        if self.log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError(f"Invalid log_level: {self.log_level}")
        if not self.regions:
            raise ValueError("regions list cannot be empty")
        return True


# Global default configuration instance
_default_config: Optional[ScanConfig] = None


def get_default_config() -> ScanConfig:
    """
    Get or create the default configuration instance.

    Returns:
        Default ScanConfig instance.
    """
    global _default_config
    if _default_config is None:
        _default_config = ScanConfig.from_env()
        _default_config.validate()
    return _default_config


def set_default_config(config: ScanConfig) -> None:
    """
    Set the default configuration instance.

    Args:
        config: ScanConfig instance to set as default.
    """
    global _default_config
    config.validate()
    _default_config = config


def reset_default_config() -> None:
    """Reset the default configuration instance (for testing)."""
    global _default_config
    _default_config = None
