"""Unit tests for AWS CloudWatch Metrics Provider."""

from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import MagicMock
from cloud_resource_inefficiency.core.enums import CloudProvider, ResourceType
from cloud_resource_inefficiency.core.models import CloudResource
from cloud_resource_inefficiency.providers.aws.metrics.cloudwatch import AWSCloudWatchMetricsProvider


class TestAWSCloudWatchMetricsProvider(unittest.TestCase):

    def test_cloudwatch_metrics_provider_aggregates_datapoints(self):
        mock_factory = MagicMock()
        mock_cw_client = MagicMock()

        mock_cw_client.get_metric_statistics.return_value = {
            "Datapoints": [
                {"Sum": 100.0, "Average": 10.0, "Maximum": 50.0, "Unit": "Count"},
                {"Sum": 200.0, "Average": 20.0, "Maximum": 80.0, "Unit": "Count"},
            ]
        }
        mock_factory.get_client.return_value = mock_cw_client

        provider = AWSCloudWatchMetricsProvider(client_factory=mock_factory)
        self.assertEqual(provider.provider, CloudProvider.AWS)

        res = CloudResource(
            resource_id="vol-12345",
            name="test-vol",
            provider=CloudProvider.AWS,
            resource_type=ResourceType.AWS_EBS_VOLUME,
            region="us-east-1",
        )

        now = datetime.now(timezone.utc)
        summary = provider.get_metric_summary(
            resource=res,
            metric_name="VolumeReadOps",
            start_time=now - timedelta(days=14),
            end_time=now,
            statistic="Sum",
        )

        self.assertEqual(summary.metric_name, "VolumeReadOps")
        self.assertEqual(summary.total_value, 300.0)
        self.assertEqual(summary.average_value, 15.0)
        self.assertEqual(summary.maximum_value, 80.0)
        self.assertEqual(summary.datapoint_count, 2)
        self.assertEqual(summary.additional_info["status"], "OK")

    def test_cloudwatch_metrics_provider_handles_no_data(self):
        mock_factory = MagicMock()
        mock_cw_client = MagicMock()
        mock_cw_client.get_metric_statistics.return_value = {"Datapoints": []}
        mock_factory.get_client.return_value = mock_cw_client

        provider = AWSCloudWatchMetricsProvider(client_factory=mock_factory)
        res = CloudResource(
            resource_id="vol-empty",
            name="empty-vol",
            provider=CloudProvider.AWS,
            resource_type=ResourceType.AWS_EBS_VOLUME,
            region="us-east-1",
        )

        now = datetime.now(timezone.utc)
        summary = provider.get_metric_summary(
            resource=res,
            metric_name="VolumeReadOps",
            start_time=now - timedelta(days=14),
            end_time=now,
        )

        self.assertEqual(summary.total_value, 0.0)
        self.assertEqual(summary.datapoint_count, 0)
        self.assertEqual(summary.additional_info["status"], "NO_DATA")


if __name__ == "__main__":
    unittest.main()
