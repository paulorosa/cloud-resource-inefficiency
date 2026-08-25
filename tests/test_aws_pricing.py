"""Unit tests for AWS Pricing Provider."""

import unittest
from unittest.mock import MagicMock
from cloud_resource_inefficiency.core.enums import CloudProvider, ResourceType
from cloud_resource_inefficiency.core.models import CloudResource
from cloud_resource_inefficiency.providers.aws.pricing.aws_pricing import AWSPricingProvider


class TestAWSPricingProvider(unittest.TestCase):

    def test_pricing_ebs_gp3_baseline(self):
        provider = AWSPricingProvider(use_remote_api=False)
        res = CloudResource(
            resource_id="vol-gp3",
            name="test-gp3",
            provider=CloudProvider.AWS,
            resource_type=ResourceType.AWS_EBS_VOLUME,
            region="us-east-1",
            raw_metadata={
                "volume_type": "gp3",
                "size_gib": 100,
                "iops": 3000,       # baseline free
                "throughput": 125,  # baseline free
            },
        )

        pricing = provider.get_resource_pricing(res)
        # 100 GiB * $0.08 = $8.00
        self.assertEqual(pricing.monthly_cost, 8.0)
        self.assertEqual(pricing.cost_breakdown["storage_cost"], 8.0)
        self.assertEqual(pricing.cost_breakdown["iops_cost"], 0.0)
        self.assertEqual(pricing.cost_breakdown["throughput_cost"], 0.0)

    def test_pricing_ebs_gp3_with_extra_iops_and_throughput(self):
        provider = AWSPricingProvider(use_remote_api=False)
        res = CloudResource(
            resource_id="vol-gp3-extra",
            name="test-gp3-extra",
            provider=CloudProvider.AWS,
            resource_type=ResourceType.AWS_EBS_VOLUME,
            region="us-east-1",
            raw_metadata={
                "volume_type": "gp3",
                "size_gib": 100,
                "iops": 5000,       # 2000 extra * $0.005 = $10.00
                "throughput": 225,  # 100 MB/s extra * $0.04 = $4.00
            },
        )

        pricing = provider.get_resource_pricing(res)
        # Storage: 100 * 0.08 = 8.0
        # IOPS: 2000 * 0.005 = 10.0
        # Throughput: 100 * 0.04 = 4.0
        # Total = 22.0
        self.assertEqual(round(pricing.monthly_cost, 2), 22.0)
        self.assertEqual(round(pricing.cost_breakdown["storage_cost"], 2), 8.0)
        self.assertEqual(round(pricing.cost_breakdown["iops_cost"], 2), 10.0)
        self.assertEqual(round(pricing.cost_breakdown["throughput_cost"], 2), 4.0)

    def test_pricing_ebs_io1(self):
        provider = AWSPricingProvider(use_remote_api=False)
        res = CloudResource(
            resource_id="vol-io1",
            name="test-io1",
            provider=CloudProvider.AWS,
            resource_type=ResourceType.AWS_EBS_VOLUME,
            region="us-east-1",
            raw_metadata={
                "volume_type": "io1",
                "size_gib": 200,
                "iops": 1000,  # 1000 * 0.065 = $65.00
            },
        )

        pricing = provider.get_resource_pricing(res)
        # Storage: 200 * 0.125 = $25.00
        # IOPS: 1000 * 0.065 = $65.00
        # Total = $90.00
        self.assertEqual(round(pricing.monthly_cost, 2), 90.0)
        self.assertEqual(round(pricing.cost_breakdown["storage_cost"], 2), 25.0)
        self.assertEqual(round(pricing.cost_breakdown["iops_cost"], 2), 65.0)

    def test_pricing_remote_api_fallback_on_error(self):
        mock_factory = MagicMock()
        mock_pricing_client = MagicMock()
        mock_pricing_client.get_products.side_effect = Exception("AccessDeniedException")
        mock_factory.get_client.return_value = mock_pricing_client

        provider = AWSPricingProvider(client_factory=mock_factory, use_remote_api=True)
        res = CloudResource(
            resource_id="vol-gp2",
            name="test-gp2",
            provider=CloudProvider.AWS,
            resource_type=ResourceType.AWS_EBS_VOLUME,
            region="us-east-1",
            raw_metadata={
                "volume_type": "gp2",
                "size_gib": 50,
            },
        )

        pricing = provider.get_resource_pricing(res)
        # gp2 in us-east-1 is $0.10/GiB -> 50 * 0.10 = $5.00
        self.assertEqual(pricing.monthly_cost, 5.0)
        self.assertEqual(pricing.rate_source, "default_rates_table")


if __name__ == "__main__":
    unittest.main()
