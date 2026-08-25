"""Unit tests for core models, enums, serialization, and registry."""

import unittest

from cloud_resource_inefficiency.core.enums import (
    CloudProvider,
    ConfidenceLevel,
    InefficiencyCategory,
    ResourceType,
    RiskLevel,
)
from cloud_resource_inefficiency.core.models import (
    CloudResource,
    Opportunity,
    ScanResult,
)
from cloud_resource_inefficiency.core.registry import InefficiencyRegistry
from cloud_resource_inefficiency.formatters.output import ScanResultFormatter


class TestCoreModels(unittest.TestCase):

    def test_cloud_resource_model_and_tag_lookup(self):
        res = CloudResource(
            resource_id="vol-12345",
            name="test-vol",
            provider=CloudProvider.AWS,
            resource_type=ResourceType.AWS_EBS_VOLUME,
            region="us-east-1",
            tags={"Environment": "Production", "cost_center": "FinOps"},
        )
        self.assertEqual(res.resource_id, "vol-12345")
        self.assertEqual(res.get_tag("environment"), "Production")
        self.assertEqual(res.get_tag("COST_CENTER"), "FinOps")
        self.assertEqual(res.get_tag("missing", default="default_val"), "default_val")

    def test_opportunity_serialization(self):
        res = CloudResource(
            resource_id="vol-12345",
            name="unused-vol",
            provider=CloudProvider.AWS,
            resource_type=ResourceType.AWS_EBS_VOLUME,
            region="us-east-1",
        )
        opp = Opportunity(
            rule_id="CER-0066",
            title="Inactive and Detached EBS Volume",
            description="EBS volume is detached and inactive.",
            category=InefficiencyCategory.UNATTACHED_STORAGE,
            resource=res,
            estimated_monthly_savings=25.50,
            currency="USD",
            confidence_level=ConfidenceLevel.HIGH,
            risk_level=RiskLevel.LOW,
            recommended_actions=["Delete volume"],
            remediation_command="aws ec2 delete-volume --volume-id vol-12345",
        )

        d = opp.to_dict()
        self.assertEqual(d["rule_id"], "CER-0066")
        self.assertEqual(d["estimated_monthly_savings"], 25.50)
        self.assertEqual(d["resource"]["resource_id"], "vol-12345")
        self.assertEqual(d["confidence_level"], "HIGH")
        self.assertEqual(d["remediation_command"], "aws ec2 delete-volume --volume-id vol-12345")

    def test_scan_result_aggregations_and_formatters(self):
        res = CloudResource(
            resource_id="vol-1",
            name="v1",
            provider=CloudProvider.AWS,
            resource_type=ResourceType.AWS_EBS_VOLUME,
            region="us-east-1",
        )
        opp1 = Opportunity(
            rule_id="CER-0066",
            title="Test 1",
            description="Desc",
            category=InefficiencyCategory.UNATTACHED_STORAGE,
            resource=res,
            estimated_monthly_savings=10.0,
        )
        opp2 = Opportunity(
            rule_id="CER-0066",
            title="Test 2",
            description="Desc",
            category=InefficiencyCategory.UNATTACHED_STORAGE,
            resource=res,
            estimated_monthly_savings=20.0,
        )

        result = ScanResult(opportunities=[opp1, opp2], scanned_resources_count=5)
        self.assertEqual(result.total_estimated_monthly_savings, 30.0)
        self.assertEqual(result.opportunities_count, 2)

        # Test formatters
        json_out = ScanResultFormatter.to_json(result)
        self.assertIn('"total_estimated_monthly_savings": 30.0', json_out)

        text_out = ScanResultFormatter.to_text_summary(result)
        self.assertIn("CLOUD FINANCIAL INEFFICIENCY SCAN REPORT", text_out)
        self.assertIn("$30.00 USD", text_out)

        md_out = ScanResultFormatter.to_markdown(result)
        self.assertIn("# Cloud Financial Inefficiency Scan Report", md_out)
        self.assertIn("**$30.00 USD**", md_out)

    def test_markdown_formatter_sanitizes_injection_and_pipes(self):
        res = CloudResource(
            resource_id="vol-12345",
            name="app|database\n<script>alert(1)</script>",
            provider=CloudProvider.AWS,
            resource_type=ResourceType.AWS_EBS_VOLUME,
            region="us-east-1",
        )
        opp = Opportunity(
            rule_id="CER-0066",
            title="Test",
            description="Desc",
            category=InefficiencyCategory.UNATTACHED_STORAGE,
            resource=res,
            estimated_monthly_savings=10.0,
            recommended_actions=["Action with | pipe and <tags>"],
        )
        result = ScanResult(opportunities=[opp], scanned_resources_count=1)
        md_out = ScanResultFormatter.to_markdown(result)

        # Ensure pipes are escaped and HTML is sanitized
        self.assertIn(r"app\|database &lt;script&gt;alert(1)&lt;/script&gt;", md_out)
        self.assertIn(r"Action with \| pipe and &lt;tags&gt;", md_out)
        self.assertNotIn("<script>", md_out)

    def test_registry_operations(self):
        registry = InefficiencyRegistry()
        self.assertEqual(len(registry.get_all_rules()), 0)


if __name__ == "__main__":
    unittest.main()
