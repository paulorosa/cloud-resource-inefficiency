"""Tests for centralized configuration management."""

import os
import tempfile
from pathlib import Path

import pytest

from cloud_resource_inefficiency.config import (
    ScanConfig,
    get_default_config,
    reset_default_config,
    set_default_config,
)


class TestScanConfigDefaults:
    """Tests for ScanConfig default values."""

    def test_config_has_default_values(self) -> None:
        """ScanConfig should have sensible default values."""
        config = ScanConfig()
        assert config.lookback_days == 14
        assert config.max_allowed_io_ops == 0.0
        assert config.timeout_seconds == 300
        assert config.retry_max_attempts == 3
        assert config.log_level == "INFO"
        assert config.regions == ["us-east-1"]

    def test_config_can_be_customized(self) -> None:
        """ScanConfig should accept custom values."""
        config = ScanConfig(
            lookback_days=30,
            max_allowed_io_ops=100.0,
            log_level="DEBUG",
            regions=["us-east-1", "us-west-2"],
        )
        assert config.lookback_days == 30
        assert config.max_allowed_io_ops == 100.0
        assert config.log_level == "DEBUG"
        assert config.regions == ["us-east-1", "us-west-2"]


class TestScanConfigFromEnv:
    """Tests for loading config from environment variables."""

    def test_from_env_with_defaults(self) -> None:
        """from_env should use env vars or defaults."""
        # Save original env vars
        original_vars = {
            "CRI_LOOKBACK_DAYS": os.getenv("CRI_LOOKBACK_DAYS"),
            "CRI_LOG_LEVEL": os.getenv("CRI_LOG_LEVEL"),
        }

        try:
            # Clear env vars to test defaults
            os.environ.pop("CRI_LOOKBACK_DAYS", None)
            os.environ.pop("CRI_LOG_LEVEL", None)

            config = ScanConfig.from_env()
            assert config.lookback_days == 14
            assert config.log_level == "INFO"
        finally:
            # Restore original env vars
            for key, val in original_vars.items():
                if val is not None:
                    os.environ[key] = val
                else:
                    os.environ.pop(key, None)

    def test_from_env_reads_env_variables(self) -> None:
        """from_env should read CRI_ prefixed environment variables."""
        original_vars = {
            "CRI_LOOKBACK_DAYS": os.getenv("CRI_LOOKBACK_DAYS"),
            "CRI_MAX_ALLOWED_IO_OPS": os.getenv("CRI_MAX_ALLOWED_IO_OPS"),
            "CRI_LOG_LEVEL": os.getenv("CRI_LOG_LEVEL"),
            "CRI_REGIONS": os.getenv("CRI_REGIONS"),
        }

        try:
            os.environ["CRI_LOOKBACK_DAYS"] = "30"
            os.environ["CRI_MAX_ALLOWED_IO_OPS"] = "150.5"
            os.environ["CRI_LOG_LEVEL"] = "DEBUG"
            os.environ["CRI_REGIONS"] = "us-east-1,eu-west-1,ap-southeast-1"

            config = ScanConfig.from_env()
            assert config.lookback_days == 30
            assert config.max_allowed_io_ops == 150.5
            assert config.log_level == "DEBUG"
            assert config.regions == ["us-east-1", "eu-west-1", "ap-southeast-1"]
        finally:
            for key, val in original_vars.items():
                if val is not None:
                    os.environ[key] = val
                else:
                    os.environ.pop(key, None)

    def test_from_env_parses_resource_types(self) -> None:
        """from_env should parse comma-separated resource types."""
        original_var = os.getenv("CRI_RESOURCE_TYPES")

        try:
            os.environ["CRI_RESOURCE_TYPES"] = "aws_ebs_volume,gcp_gcs_bucket,azure_managed_disk"
            config = ScanConfig.from_env()
            assert config.resource_types == ["aws_ebs_volume", "gcp_gcs_bucket", "azure_managed_disk"]
        finally:
            if original_var:
                os.environ["CRI_RESOURCE_TYPES"] = original_var
            else:
                os.environ.pop("CRI_RESOURCE_TYPES", None)


class TestScanConfigFromYaml:
    """Tests for loading config from YAML files."""

    def test_from_yaml_file_valid(self) -> None:
        """from_yaml_file should load valid YAML configuration."""
        yaml_content = """
lookback_days: 30
max_allowed_io_ops: 200.0
timeout_seconds: 600
log_level: DEBUG
regions:
  - us-east-1
  - us-west-2
  - eu-west-1
resource_types:
  - aws_ebs_volume
  - gcp_gcs_bucket
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                config = ScanConfig.from_yaml_file(f.name)
                assert config.lookback_days == 30
                assert config.max_allowed_io_ops == 200.0
                assert config.timeout_seconds == 600
                assert config.log_level == "DEBUG"
                assert config.regions == ["us-east-1", "us-west-2", "eu-west-1"]
                assert config.resource_types == ["aws_ebs_volume", "gcp_gcs_bucket"]
            finally:
                os.unlink(f.name)

    def test_from_yaml_file_not_found(self) -> None:
        """from_yaml_file should raise FileNotFoundError for missing files."""
        with pytest.raises(FileNotFoundError):
            ScanConfig.from_yaml_file("/nonexistent/path/config.yaml")

    def test_from_yaml_file_optional_with_path(self) -> None:
        """from_yaml_file_optional should use YAML file if provided."""
        yaml_content = """
lookback_days: 45
log_level: WARNING
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                config = ScanConfig.from_yaml_file_optional(f.name)
                assert config.lookback_days == 45
                assert config.log_level == "WARNING"
            finally:
                os.unlink(f.name)

    def test_from_yaml_file_optional_without_path(self) -> None:
        """from_yaml_file_optional should use env vars if no path provided."""
        original_var = os.getenv("CRI_LOOKBACK_DAYS")

        try:
            os.environ["CRI_LOOKBACK_DAYS"] = "60"
            config = ScanConfig.from_yaml_file_optional(None)
            assert config.lookback_days == 60
        finally:
            if original_var:
                os.environ["CRI_LOOKBACK_DAYS"] = original_var
            else:
                os.environ.pop("CRI_LOOKBACK_DAYS", None)


class TestScanConfigValidation:
    """Tests for configuration validation."""

    def test_validate_succeeds_with_valid_config(self) -> None:
        """validate should return True for valid configuration."""
        config = ScanConfig(
            lookback_days=30,
            timeout_seconds=300,
            retry_max_attempts=3,
            log_level="INFO",
            regions=["us-east-1"],
        )
        assert config.validate() is True

    def test_validate_fails_with_invalid_lookback_days(self) -> None:
        """validate should raise for invalid lookback_days."""
        config = ScanConfig(lookback_days=0)
        with pytest.raises(ValueError, match="lookback_days must be >= 1"):
            config.validate()

    def test_validate_fails_with_invalid_log_level(self) -> None:
        """validate should raise for invalid log_level."""
        config = ScanConfig(log_level="INVALID")
        with pytest.raises(ValueError, match="Invalid log_level"):
            config.validate()

    def test_validate_fails_with_empty_regions(self) -> None:
        """validate should raise for empty regions list."""
        config = ScanConfig(regions=[])
        with pytest.raises(ValueError, match="regions list cannot be empty"):
            config.validate()

    def test_validate_fails_with_invalid_retry_backoff_factor(self) -> None:
        """validate should raise for backoff factor < 1.0."""
        config = ScanConfig(retry_backoff_factor=0.5)
        with pytest.raises(ValueError, match="retry_backoff_factor must be >= 1.0"):
            config.validate()


class TestScanConfigToDict:
    """Tests for converting config to dictionary."""

    def test_to_dict_returns_all_fields(self) -> None:
        """to_dict should return all configuration fields."""
        config = ScanConfig(
            lookback_days=25,
            max_allowed_io_ops=75.0,
            log_level="DEBUG",
        )
        config_dict = config.to_dict()

        assert config_dict["lookback_days"] == 25
        assert config_dict["max_allowed_io_ops"] == 75.0
        assert config_dict["log_level"] == "DEBUG"
        assert "retry_max_attempts" in config_dict
        assert "timeout_seconds" in config_dict


class TestGlobalDefaultConfig:
    """Tests for global default configuration."""

    def test_get_default_config_returns_instance(self) -> None:
        """get_default_config should return a ScanConfig instance."""
        reset_default_config()
        config = get_default_config()
        assert isinstance(config, ScanConfig)

    def test_get_default_config_singleton(self) -> None:
        """get_default_config should return same instance on subsequent calls."""
        reset_default_config()
        config1 = get_default_config()
        config2 = get_default_config()
        assert config1 is config2

    def test_set_default_config(self) -> None:
        """set_default_config should replace default instance."""
        reset_default_config()
        custom_config = ScanConfig(lookback_days=100)
        set_default_config(custom_config)

        retrieved = get_default_config()
        assert retrieved is custom_config
        assert retrieved.lookback_days == 100

    def test_set_default_config_validates(self) -> None:
        """set_default_config should validate before setting."""
        reset_default_config()
        invalid_config = ScanConfig(lookback_days=0)

        with pytest.raises(ValueError):
            set_default_config(invalid_config)

    def test_reset_default_config(self) -> None:
        """reset_default_config should clear the cached instance."""
        reset_default_config()
        config1 = get_default_config()

        reset_default_config()
        # Force env var to ensure new instance is different
        original_var = os.getenv("CRI_LOOKBACK_DAYS")

        try:
            os.environ["CRI_LOOKBACK_DAYS"] = "99"
            config2 = get_default_config()
            assert config2.lookback_days == 99
        finally:
            if original_var:
                os.environ["CRI_LOOKBACK_DAYS"] = original_var
            else:
                os.environ.pop("CRI_LOOKBACK_DAYS", None)
