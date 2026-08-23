"""Unit tests for AWS EBS Collector."""

import unittest
from unittest.mock import MagicMock
from cloud_resource_inefficiency.core.enums import CloudProvider, ResourceType
from cloud_resource_inefficiency.providers.aws.collectors.ebs_collector import AWSEBSCollector


class TestAWSEBSCollector(unittest.TestCase):

    def test_ebs_collector_parses_volumes(self):
        mock_factory = MagicMock()
        mock_ec2_client = MagicMock()
        mock_paginator = MagicMock()

        mock_paginator.paginate.return_value = [
            {
                "Volumes": [
                    {
                        "VolumeId": "vol-123456",
                        "Size": 50,
                        "VolumeType": "gp3",
                        "State": "available",
                        "Iops": 3000,
                        "Throughput": 125,
                        "AvailabilityZone": "us-east-1a",
                        "SnapshotId": "snap-987",
                        "Attachments": [],
                        "Tags": [{"Key": "Name", "Value": "dev-backup-vol"}],
                    },
                    {
                        "VolumeId": "vol-789012",
                        "Size": 200,
                        "VolumeType": "io1",
                        "State": "in-use",
                        "Iops": 5000,
                        "Throughput": 0,
                        "AvailabilityZone": "us-east-1b",
                        "SnapshotId": "",
                        "Attachments": [{"InstanceId": "i-abcdef"}],
                        "Tags": [{"Key": "Environment", "Value": "Prod"}],
                    },
                ]
            }
        ]
        mock_ec2_client.get_paginator.return_value = mock_paginator
        mock_factory.get_client.return_value = mock_ec2_client

        collector = AWSEBSCollector(client_factory=mock_factory)
        self.assertEqual(collector.provider, CloudProvider.AWS)
        self.assertEqual(collector.resource_type, ResourceType.AWS_EBS_VOLUME)

        resources = collector.collect(region="us-east-1")

        self.assertEqual(len(resources), 2)
        self.assertEqual(resources[0].resource_id, "vol-123456")
        self.assertEqual(resources[0].status, "available")
        self.assertEqual(resources[0].name, "dev-backup-vol")
        self.assertFalse(resources[0].raw_metadata["is_attached"])
        self.assertEqual(resources[0].raw_metadata["size_gib"], 50)

        self.assertEqual(resources[1].resource_id, "vol-789012")
        self.assertEqual(resources[1].status, "in-use")
        self.assertTrue(resources[1].raw_metadata["is_attached"])


if __name__ == "__main__":
    unittest.main()
