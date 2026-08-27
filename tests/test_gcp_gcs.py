"""Tests for GCP GCS collector, metrics provider, and pricing."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from cloud_resource_inefficiency.core.enums import (
    CloudProvider,
    ResourceType,
)
from cloud_resource_inefficiency.core.models import (
    CloudResource,
    MetricSummary,
    PricingDetails,
)
from cloud_resource_inefficiency.providers.gcp.collectors.gcs_collector import GCSCollector
from cloud_resource_inefficiency.providers.gcp.metrics.cloud_monitoring import (
    GCPMonitoringMetricsProvider,
)
from cloud_resource_inefficiency.providers.gcp.pricing.gcp_pricing import GCPPricingProvider


@pytest.fixture
def mock_gcp_client_factory():
    """Mock GCP client factory."""
    factory = MagicMock()
    return factory


@pytest.fixture
def gcp_gcs_bucket_resource():
    """Returns a mock GCS bucket resource."""
    return CloudResource(
        resource_id="my-bucket-prod",
        name="my-bucket-prod",
        provider=CloudProvider.GCP,
        resource_type=ResourceType.GCP_GCS_BUCKET,
        region="us-central1",
        account_id="project-12345",
        tags={"Environment": "Production"},
        created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
        status="active",
        raw_metadata={
            "storage_class": "STANDARD",
            "location": "us-central1",
            "size_bytes": 1099511627776,  # 1 TB
        },
    )


class TestGCSCollector:
    """Tests for GCS bucket collector."""

    def test_provider_is_gcp(self, mock_gcp_client_factory):
        """GCS collector should report provider as GCP."""
        collector = GCSCollector(client_factory=mock_gcp_client_factory)
        assert collector.provider == CloudProvider.GCP

    def test_resource_type_is_gcs_bucket(self, mock_gcp_client_factory):
        """GCS collector should report resource type as GCS bucket."""
        collector = GCSCollector(client_factory=mock_gcp_client_factory)
        assert collector.resource_type == ResourceType.GCP_GCS_BUCKET

    @patch("cloud_resource_inefficiency.providers.gcp.collectors.gcs_collector.GCPClientFactory")
    def test_collect_returns_resources(self, mock_factory_class, gcp_gcs_bucket_resource):
        """Collect should return GCS bucket resources."""
        mock_factory = MagicMock()
        mock_factory_class.return_value = mock_factory

        mock_storage_client = MagicMock()
        mock_factory.get_storage_client.return_value = mock_storage_client

        # Mock bucket iterator
        mock_bucket = MagicMock()
        mock_bucket.name = gcp_gcs_bucket_resource.resource_id
        mock_bucket.storage_class = "STANDARD"
        mock_bucket.location = "us-central1"
        mock_bucket.time_created = datetime(2023, 1, 1, tzinfo=timezone.utc)

        mock_storage_client.list_buckets.return_value = [mock_bucket]

        collector = GCSCollector(client_factory=mock_factory)
        resources = collector.collect(region="us-central1")

        assert isinstance(resources, list)

    def test_collect_with_default_factory(self):
        """Collect should work with default client factory."""
        with patch("cloud_resource_inefficiency.providers.gcp.client_factory.GCPClientFactory"):
            collector = GCSCollector()
            assert collector is not None


class TestGCPMonitoringMetricsProvider:
    """Tests for GCP Monitoring metrics provider."""

    def test_provider_is_gcp(self, mock_gcp_client_factory):
        """Metrics provider should report provider as GCP."""
        provider = GCPMonitoringMetricsProvider(client_factory=mock_gcp_client_factory)
        assert provider.provider == CloudProvider.GCP

    def test_get_metric_summary_returns_metric(self, mock_gcp_client_factory, gcp_gcs_bucket_resource):
        """Get metric summary should return MetricSummary object."""
        mock_monitoring_client = MagicMock()
        mock_gcp_client_factory.get_monitoring_client.return_value = mock_monitoring_client

        provider = GCPMonitoringMetricsProvider(client_factory=mock_gcp_client_factory)

        # Mock the metric query result
        mock_monitoring_client.list_time_series.return_value = MagicMock(
            time_series=[MagicMock(points=[MagicMock(value=MagicMock(double_value=1000.0))])]
        )

        metric = provider.get_metric_summary(
            resource=gcp_gcs_bucket_resource,
            metric_name="storage.googleapis.com/storage/total_bytes",
            period_days=30,
        )

        assert isinstance(metric, MetricSummary)
        assert metric.metric_name == "storage.googleapis.com/storage/total_bytes"


class TestGCPPricingProvider:
    """Tests for GCP pricing provider."""

    def test_provider_is_gcp(self):
        """Pricing provider should report provider as GCP."""
        provider = GCPPricingProvider()
        assert provider.provider == CloudProvider.GCP

    def test_get_resource_pricing_returns_pricing_details(self, gcp_gcs_bucket_resource):
        """Get resource pricing should return PricingDetails object."""
        provider = GCPPricingProvider()
        pricing = provider.get_resource_pricing(resource=gcp_gcs_bucket_resource)

        assert isinstance(pricing, PricingDetails)
        assert pricing.currency == "USD"
        assert pricing.monthly_cost >= 0

    def test_pricing_calculation_for_standard_storage(self, gcp_gcs_bucket_resource):
        """Pricing for STANDARD storage class should use correct rate."""
        provider = GCPPricingProvider()
        pricing = provider.get_resource_pricing(resource=gcp_gcs_bucket_resource)

        # 1 TB = 1099511627776 bytes
        # STANDARD rate ~$0.020 per GB
        assert pricing.monthly_cost > 0
        assert "storage_cost" in pricing.cost_breakdown

    def test_pricing_for_different_storage_classes(self, gcp_gcs_bucket_resource):
        """Pricing should differ for different storage classes."""
        provider = GCPPricingProvider()

        # Test STANDARD
        gcp_gcs_bucket_resource.raw_metadata["storage_class"] = "STANDARD"
        pricing_standard = provider.get_resource_pricing(resource=gcp_gcs_bucket_resource)

        # Test COLDLINE
        gcp_gcs_bucket_resource.raw_metadata["storage_class"] = "COLDLINE"
        pricing_coldline = provider.get_resource_pricing(resource=gcp_gcs_bucket_resource)

        # COLDLINE should be cheaper than STANDARD
        assert pricing_coldline.monthly_cost < pricing_standard.monthly_cost
