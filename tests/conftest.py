"""Pytest fixtures and test doubles."""

from datetime import datetime, timezone
from unittest.mock import MagicMock
import pytest

from cloud_resource_inefficiency.core.enums import (
    CloudProvider,
    ConfidenceLevel,
    InefficiencyCategory,
    ResourceType,
    RiskLevel,
)
from cloud_resource_inefficiency.core.models import (
    CloudResource,
    MetricSummary,
    Opportunity,
    PricingDetails,
)


@pytest.fixture
def mock_ebs_resource_detached():
    """Returns a detached (available) EBS volume resource."""
    return CloudResource(
        resource_id="vol-0123456789abcdef0",
        name="test-unattached-volume",
        provider=CloudProvider.AWS,
        resource_type=ResourceType.AWS_EBS_VOLUME,
        region="us-east-1",
        account_id="123456789012",
        tags={"Environment": "Dev", "Project": "FinOps"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        status="available",
        raw_metadata={
            "size_gib": 100,
            "volume_type": "gp3",
            "iops": 3000,
            "throughput": 125,
            "is_attached": False,
            "attachments": [],
            "snapshot_id": "snap-abcdef123456",
        },
    )


@pytest.fixture
def mock_ebs_resource_attached():
    """Returns an attached (in-use) EBS volume resource."""
    return CloudResource(
        resource_id="vol-0987654321fedcba0",
        name="test-attached-volume",
        provider=CloudProvider.AWS,
        resource_type=ResourceType.AWS_EBS_VOLUME,
        region="us-east-1",
        account_id="123456789012",
        tags={"Environment": "Prod"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        status="in-use",
        raw_metadata={
            "size_gib": 500,
            "volume_type": "io1",
            "iops": 10000,
            "throughput": 0,
            "is_attached": True,
            "attachments": [{"InstanceId": "i-1234567890abcdef0", "State": "attached"}],
            "snapshot_id": None,
        },
    )


@pytest.fixture
def mock_metrics_provider_zero_io():
    """Metrics provider returning 0 IO ops."""
    provider = MagicMock()
    provider.provider = CloudProvider.AWS
    provider.get_metric_summary.return_value = MetricSummary(
        metric_name="VolumeReadOps",
        unit="Count",
        period_days=14,
        total_value=0.0,
        average_value=0.0,
        maximum_value=0.0,
        datapoint_count=14,
    )
    return provider


@pytest.fixture
def mock_metrics_provider_active_io():
    """Metrics provider returning active IO ops."""
    provider = MagicMock()
    provider.provider = CloudProvider.AWS
    provider.get_metric_summary.return_value = MetricSummary(
        metric_name="VolumeReadOps",
        unit="Count",
        period_days=14,
        total_value=150000.0,
        average_value=10714.28,
        maximum_value=25000.0,
        datapoint_count=14,
    )
    return provider


@pytest.fixture
def mock_pricing_provider():
    """Pricing provider returning standard mock cost."""
    provider = MagicMock()
    provider.provider = CloudProvider.AWS
    provider.get_resource_pricing.return_value = PricingDetails(
        monthly_cost=8.0,
        currency="USD",
        rate_source="default_rates_table",
        unit_rates={"storage_rate_per_gib": 0.08},
        cost_breakdown={"storage_cost": 8.0, "iops_cost": 0.0, "throughput_cost": 0.0},
    )
    return provider
