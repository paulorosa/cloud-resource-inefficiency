"""End-to-end integration tests for InefficiencyScanner with mocked providers."""

from datetime import datetime, timezone
import unittest
from unittest.mock import MagicMock

from cloud_resource_inefficiency.core.enums import (
    CloudProvider,
    ResourceType,
)
from cloud_resource_inefficiency.core.models import (
    CloudResource,
    MetricSummary,
    PricingDetails,
)
from cloud_resource_inefficiency.core.registry import InefficiencyRegistry
from cloud_resource_inefficiency.engine.scanner import InefficiencyScanner
from cloud_resource_inefficiency.providers.aws.rules.ebs_inactive_detached import InactiveDetachedEBSVolumeRule


class TestScannerIntegration(unittest.TestCase):

    def setUp(self):
        self.mock_ebs_detached = CloudResource(
            resource_id="vol-0123456789abcdef0",
            name="test-unattached-volume",
            provider=CloudProvider.AWS,
            resource_type=ResourceType.AWS_EBS_VOLUME,
            region="us-east-1",
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

        self.mock_ebs_attached = CloudResource(
            resource_id="vol-0987654321fedcba0",
            name="test-attached-volume",
            provider=CloudProvider.AWS,
            resource_type=ResourceType.AWS_EBS_VOLUME,
            region="us-east-1",
            status="in-use",
            raw_metadata={
                "size_gib": 500,
                "volume_type": "io1",
                "is_attached": True,
                "attachments": [{"InstanceId": "i-123"}],
            },
        )

        self.mock_metrics = MagicMock()
        self.mock_metrics.provider = CloudProvider.AWS
        self.mock_metrics.get_metric_summary.return_value = MetricSummary(
            metric_name="VolumeReadOps",
            unit="Count",
            period_days=14,
            total_value=0.0,
            average_value=0.0,
            maximum_value=0.0,
            datapoint_count=14,
        )

        self.mock_pricing = MagicMock()
        self.mock_pricing.provider = CloudProvider.AWS
        self.mock_pricing.get_resource_pricing.return_value = PricingDetails(
            monthly_cost=8.0,
            currency="USD",
        )

    def test_scanner_end_to_end(self):
        registry = InefficiencyRegistry()

        # Mock collector
        mock_collector = MagicMock()
        mock_collector.provider = CloudProvider.AWS
        mock_collector.resource_type = ResourceType.AWS_EBS_VOLUME
        mock_collector.collect.return_value = [
            self.mock_ebs_detached,
            self.mock_ebs_attached,
        ]

        # Register components
        registry.register_collector(mock_collector)
        registry.register_metrics_provider(self.mock_metrics)
        registry.register_pricing_provider(self.mock_pricing)
        registry.register_rule(InactiveDetachedEBSVolumeRule())

        scanner = InefficiencyScanner(
            registry=registry,
            providers=[CloudProvider.AWS],
            regions=["us-east-1"],
            auto_register_defaults=False,
        )

        result = scanner.scan(
            resource_types=[ResourceType.AWS_EBS_VOLUME],
            regions=["us-east-1"],
            lookback_days=14,
        )

        self.assertEqual(result.scanned_resources_count, 2)
        self.assertEqual(result.opportunities_count, 1)
        self.assertEqual(result.total_estimated_monthly_savings, 8.0)

        opp = result.opportunities[0]
        self.assertEqual(opp.rule_id, "AWS-EBS-001")
        self.assertEqual(opp.resource.resource_id, "vol-0123456789abcdef0")
        self.assertEqual(opp.estimated_monthly_savings, 8.0)


if __name__ == "__main__":
    unittest.main()
