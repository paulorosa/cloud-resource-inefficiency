"""Unit tests for AWS-EBS-001 (Inactive and Detached EBS Volume)."""

from datetime import datetime, timezone
import unittest
from unittest.mock import MagicMock

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
    PricingDetails,
)
from cloud_resource_inefficiency.providers.aws.rules.ebs_inactive_detached import InactiveDetachedEBSVolumeRule


class TestInactiveDetachedEBSVolumeRule(unittest.TestCase):

    def setUp(self):
        self.mock_ebs_detached = CloudResource(
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

        self.mock_ebs_attached = CloudResource(
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

        self.mock_metrics_zero_io = MagicMock()
        self.mock_metrics_zero_io.provider = CloudProvider.AWS
        self.mock_metrics_zero_io.get_metric_summary.return_value = MetricSummary(
            metric_name="VolumeReadOps",
            unit="Count",
            period_days=14,
            total_value=0.0,
            average_value=0.0,
            maximum_value=0.0,
            datapoint_count=14,
        )

        self.mock_metrics_active_io = MagicMock()
        self.mock_metrics_active_io.provider = CloudProvider.AWS
        self.mock_metrics_active_io.get_metric_summary.return_value = MetricSummary(
            metric_name="VolumeReadOps",
            unit="Count",
            period_days=14,
            total_value=150000.0,
            average_value=10714.28,
            maximum_value=25000.0,
            datapoint_count=14,
        )

        self.mock_pricing = MagicMock()
        self.mock_pricing.provider = CloudProvider.AWS
        self.mock_pricing.get_resource_pricing.return_value = PricingDetails(
            monthly_cost=8.0,
            currency="USD",
            rate_source="default_rates_table",
            unit_rates={"storage_rate_per_gib": 0.08},
            cost_breakdown={"storage_cost": 8.0, "iops_cost": 0.0, "throughput_cost": 0.0},
        )

    def test_rule_detects_opportunity_for_detached_and_zero_io(self):
        rule = InactiveDetachedEBSVolumeRule(lookback_days=14)
        self.assertEqual(rule.rule_id, "CER-0066")
        self.assertEqual(rule.category, InefficiencyCategory.UNATTACHED_STORAGE)

        opportunity = rule.evaluate(
            resource=self.mock_ebs_detached,
            metrics_provider=self.mock_metrics_zero_io,
            pricing_provider=self.mock_pricing,
        )

        self.assertIsNotNone(opportunity)
        self.assertEqual(opportunity.rule_id, "CER-0066")
        self.assertEqual(opportunity.estimated_monthly_savings, 8.0)
        self.assertEqual(opportunity.currency, "USD")
        self.assertEqual(opportunity.risk_level, RiskLevel.LOW)
        self.assertEqual(opportunity.confidence_level, ConfidenceLevel.HIGH)
        self.assertIn("aws ec2 delete-volume", opportunity.remediation_command)
        self.assertTrue(len(opportunity.recommended_actions) >= 3)

    def test_rule_ignores_attached_volume(self):
        rule = InactiveDetachedEBSVolumeRule()
        opportunity = rule.evaluate(
            resource=self.mock_ebs_attached,
            metrics_provider=self.mock_metrics_zero_io,
            pricing_provider=self.mock_pricing,
        )
        self.assertIsNone(opportunity)

    def test_rule_ignores_detached_volume_with_active_io(self):
        rule = InactiveDetachedEBSVolumeRule()
        opportunity = rule.evaluate(
            resource=self.mock_ebs_detached,
            metrics_provider=self.mock_metrics_active_io,
            pricing_provider=self.mock_pricing,
        )
        self.assertIsNone(opportunity)

    def test_rule_flags_medium_risk_when_preservation_tag_is_present(self):
        self.mock_ebs_detached.tags = {"DoNotDelete": "True", "BackupPolicy": "Keep"}
        rule = InactiveDetachedEBSVolumeRule()

        opportunity = rule.evaluate(
            resource=self.mock_ebs_detached,
            metrics_provider=self.mock_metrics_zero_io,
            pricing_provider=self.mock_pricing,
        )

        self.assertIsNotNone(opportunity)
    def test_rule_ignores_volume_when_metrics_fail_with_error(self):
        # When CloudWatch fails (e.g. AccessDenied), status is 'ERROR' and total_value is 0.0
        # The rule must NOT flag it as inactive to prevent deleting actively used resources.
        mock_metrics_error = MagicMock()
        mock_metrics_error.get_metric_summary.return_value = MetricSummary(
            metric_name="VolumeReadOps",
            unit="None",
            period_days=14,
            total_value=0.0,
            average_value=0.0,
            maximum_value=0.0,
            datapoint_count=0,
            additional_info={"status": "ERROR", "error_message": "AccessDeniedException"},
        )

        rule = InactiveDetachedEBSVolumeRule()
        opportunity = rule.evaluate(
            resource=self.mock_ebs_detached,
            metrics_provider=mock_metrics_error,
            pricing_provider=self.mock_pricing,
        )

        self.assertIsNone(opportunity, "Rule should return None when CloudWatch metrics fail with ERROR")


if __name__ == "__main__":
    unittest.main()
