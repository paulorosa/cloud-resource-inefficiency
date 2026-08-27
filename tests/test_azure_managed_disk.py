"""Tests for Azure Managed Disk discovery and inefficiency detection."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock

import pytest

from cloud_resource_inefficiency.core.enums import (
    CloudProvider,
    ConfidenceLevel,
    InefficiencyCategory,
    ResourceType,
    RiskLevel,
)
from cloud_resource_inefficiency.core.models import CloudResource, MetricSummary
from cloud_resource_inefficiency.core.registry import InefficiencyRegistry
from cloud_resource_inefficiency.providers.azure.collectors.managed_disk_collector import (
    AzureManagedDiskCollector,
)
from cloud_resource_inefficiency.providers.azure.pricing.azure_pricing import AzurePricingProvider
from cloud_resource_inefficiency.providers.azure.rules.managed_disk_inactive_detached import (
    InactiveDetachedManagedDiskRule,
)
from cloud_resource_inefficiency.providers.azure import register_azure_provider


class TestAzureManagedDisk(TestCase):
    def setUp(self):
        self.resource = CloudResource(
            resource_id="/subscriptions/123/resourceGroups/rg/providers/Microsoft.Compute/disks/disk-1",
            name="disk-1",
            provider=CloudProvider.AZURE,
            resource_type=ResourceType.AZURE_MANAGED_DISK,
            region="eastus",
            tags={"Environment": "Dev"},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            status="unattached",
            raw_metadata={"size_gib": 128, "sku": "Premium_LRS", "is_attached": False},
        )
        self.metrics = MagicMock()
        self.metrics.get_metric_summary.return_value = MetricSummary(
            metric_name="disk", unit="Count", period_days=14, total_value=0,
            average_value=0, maximum_value=0, datapoint_count=0,
        )

    def test_rule_detects_unattached_disk_without_activity(self):
        opportunity = InactiveDetachedManagedDiskRule().evaluate(
            self.resource, self.metrics, AzurePricingProvider()
        )

        self.assertIsNotNone(opportunity)
        self.assertEqual(opportunity.rule_id, "AZURE-MANAGED-DISK-001")
        self.assertEqual(opportunity.category, InefficiencyCategory.UNATTACHED_STORAGE)
        self.assertEqual(opportunity.estimated_monthly_savings, 17.28)
        self.assertEqual(opportunity.confidence_level, ConfidenceLevel.HIGH)
        self.assertEqual(opportunity.risk_level, RiskLevel.LOW)
        self.assertIn("az disk delete", opportunity.remediation_command)

    def test_rule_ignores_attached_or_active_disk(self):
        attached = self.resource
        attached.status = "attached"
        attached.raw_metadata["is_attached"] = True
        self.assertIsNone(InactiveDetachedManagedDiskRule().evaluate(attached, self.metrics, AzurePricingProvider()))

        active = self.resource
        self.metrics.get_metric_summary.return_value = MetricSummary(
            metric_name="disk", unit="Count", period_days=14, total_value=1,
            average_value=1, maximum_value=1, datapoint_count=1,
        )
        self.assertIsNone(InactiveDetachedManagedDiskRule().evaluate(active, self.metrics, AzurePricingProvider()))

    def test_collector_maps_disk_properties_and_filters_region(self):
        factory = MagicMock(subscription_id="subscription-1")
        factory.get_compute_client.return_value.disks.list.return_value = [
            SimpleNamespace(
                id=self.resource.resource_id, name="disk-1", location="eastus", tags={"Team": "FinOps"},
                time_created=self.resource.created_at, disk_size_gb=128,
                sku=SimpleNamespace(name="Premium_LRS"), managed_by=None,
                disk_iops_read_write=5000, disk_m_bps_read_write=200, os_type="Linux",
                hyper_v_generation="V2",
            ),
            SimpleNamespace(
                id="/subscriptions/123/resourceGroups/rg/providers/Microsoft.Compute/disks/disk-2",
                name="disk-2", location="westus", tags={}, time_created=None, disk_size_gb=32,
                sku=SimpleNamespace(name="Standard_LRS"), managed_by="/vm/vm-1",
            ),
        ]
        resources = AzureManagedDiskCollector(factory).collect("eastus")

        self.assertEqual(len(resources), 1)
        self.assertEqual(resources[0].status, "unattached")
        self.assertEqual(resources[0].raw_metadata["size_gib"], 128)

    def test_registration_exposes_all_azure_components(self):
        registry = InefficiencyRegistry()
        register_azure_provider(registry=registry, client_factory=MagicMock())

        self.assertIsNotNone(registry.get_collector(ResourceType.AZURE_MANAGED_DISK))
        self.assertIsNotNone(registry.get_metrics_provider(CloudProvider.AZURE))
        self.assertIsNotNone(registry.get_pricing_provider(CloudProvider.AZURE))
        self.assertEqual(len(registry.get_rules_for_provider(CloudProvider.AZURE)), 1)


@pytest.mark.parametrize("size_gib,expected_savings", [
    (32, 4.32),
    (128, 17.28),
    (256, 34.56),
    (512, 69.12),
    (1024, 138.24),
])
def test_azure_disk_pricing_by_size(size_gib: int, expected_savings: float):
    """Test Azure managed disk pricing scales correctly with size."""
    resource = CloudResource(
        resource_id="/subscriptions/123/resourceGroups/rg/providers/Microsoft.Compute/disks/disk-test",
        name="disk-test",
        provider=CloudProvider.AZURE,
        resource_type=ResourceType.AZURE_MANAGED_DISK,
        region="eastus",
        tags={},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        status="unattached",
        raw_metadata={"size_gib": size_gib, "sku": "Premium_LRS", "is_attached": False},
    )

    metrics = MagicMock()
    metrics.get_metric_summary.return_value = MetricSummary(
        metric_name="disk", unit="Count", period_days=14, total_value=0,
        average_value=0, maximum_value=0, datapoint_count=0,
    )

    rule = InactiveDetachedManagedDiskRule()
    opportunity = rule.evaluate(resource, metrics, AzurePricingProvider())

    assert opportunity is not None
    assert opportunity.estimated_monthly_savings == expected_savings


@pytest.mark.parametrize("sku,has_opportunity", [
    ("Premium_LRS", True),
    ("Premium_ZRS", True),
    ("StandardSSD_LRS", True),
    ("StandardSSD_ZRS", True),
    ("Standard_LRS", True),
])
def test_azure_rule_detects_opportunity_for_all_skus(sku: str, has_opportunity: bool):
    """Test that the rule detects inefficiency for all Azure managed disk SKUs."""
    resource = CloudResource(
        resource_id="/subscriptions/123/resourceGroups/rg/providers/Microsoft.Compute/disks/disk-sku-test",
        name="disk-sku-test",
        provider=CloudProvider.AZURE,
        resource_type=ResourceType.AZURE_MANAGED_DISK,
        region="eastus",
        tags={},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        status="unattached",
        raw_metadata={"size_gib": 128, "sku": sku, "is_attached": False},
    )

    metrics = MagicMock()
    metrics.get_metric_summary.return_value = MetricSummary(
        metric_name="disk", unit="Count", period_days=14, total_value=0,
        average_value=0, maximum_value=0, datapoint_count=0,
    )

    rule = InactiveDetachedManagedDiskRule()
    opportunity = rule.evaluate(resource, metrics, AzurePricingProvider())

    if has_opportunity:
        assert opportunity is not None
    else:
        assert opportunity is None


if __name__ == "__main__":
    import unittest

    unittest.main()