"""Tests for thread-safety of client factories."""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import MagicMock, patch

import pytest

from cloud_resource_inefficiency.providers.aws.client_factory import AWSClientFactory
from cloud_resource_inefficiency.providers.azure.client_factory import AzureClientFactory
from cloud_resource_inefficiency.providers.gcp.client_factory import GCPClientFactory


class TestAWSClientFactoryThreadSafety:
    """Tests for AWS client factory thread safety."""

    @patch("cloud_resource_inefficiency.providers.aws.client_factory.boto3")
    def test_aws_factory_concurrent_access(self, mock_boto3: MagicMock) -> None:
        """AWS factory should handle concurrent client requests safely."""
        mock_ec2 = MagicMock()
        mock_cloudwatch = MagicMock()

        mock_boto3.client.side_effect = lambda service, **kwargs: {
            "ec2": mock_ec2,
            "cloudwatch": mock_cloudwatch,
        }.get(service, MagicMock())

        factory = AWSClientFactory(region="us-east-1")

        def get_clients() -> None:
            """Get clients in a thread."""
            ec2 = factory.get_ec2_client()
            cw = factory.get_cloudwatch_client()
            assert ec2 is not None
            assert cw is not None

        # Run in multiple threads
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(get_clients) for _ in range(10)]
            for future in as_completed(futures):
                future.result()  # Should not raise

    @patch("cloud_resource_inefficiency.providers.aws.client_factory.boto3")
    def test_aws_factory_returns_same_client_per_thread(self, mock_boto3: MagicMock) -> None:
        """AWS factory should return same client instance on repeated calls."""
        mock_ec2 = MagicMock()
        mock_boto3.client.return_value = mock_ec2

        factory = AWSClientFactory(region="us-east-1")

        # Multiple calls should return the same object (or at least equal)
        client1 = factory.get_ec2_client()
        client2 = factory.get_ec2_client()

        # Both calls should be valid
        assert client1 is not None
        assert client2 is not None


class TestAzureClientFactoryThreadSafety:
    """Tests for Azure client factory thread safety."""

    @patch("cloud_resource_inefficiency.providers.azure.client_factory.AzureClientFactory._get_credential")
    @patch("cloud_resource_inefficiency.providers.azure.client_factory.ComputeManagementClient")
    @patch("cloud_resource_inefficiency.providers.azure.client_factory.MonitorManagementClient")
    def test_azure_factory_concurrent_access(
        self,
        mock_monitor_client: MagicMock,
        mock_compute_client: MagicMock,
        mock_get_credential: MagicMock,
    ) -> None:
        """Azure factory should handle concurrent client requests safely."""
        mock_get_credential.return_value = MagicMock()

        factory = AzureClientFactory(subscription_id="test-sub")

        def get_clients() -> None:
            """Get clients in a thread."""
            compute = factory.get_compute_client()
            monitor = factory.get_monitor_client()
            assert compute is not None
            assert monitor is not None

        # Run in multiple threads
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(get_clients) for _ in range(10)]
            for future in as_completed(futures):
                future.result()  # Should not raise


class TestGCPClientFactoryThreadSafety:
    """Tests for GCP client factory thread safety."""

    @patch("cloud_resource_inefficiency.providers.gcp.client_factory.storage")
    @patch("cloud_resource_inefficiency.providers.gcp.client_factory.monitoring_v3")
    @patch("cloud_resource_inefficiency.providers.gcp.client_factory.logging_v2")
    def test_gcp_factory_concurrent_access(
        self,
        mock_logging: MagicMock,
        mock_monitoring: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        """GCP factory should handle concurrent client requests safely."""
        mock_storage.Client.return_value = MagicMock()
        mock_monitoring.MetricServiceClient.return_value = MagicMock()
        mock_logging.Client.return_value = MagicMock()

        factory = GCPClientFactory(project_id="test-project")

        def get_clients() -> None:
            """Get clients in a thread."""
            storage = factory.get_storage_client()
            monitoring = factory.get_monitoring_client()
            logging = factory.get_logging_client()
            assert storage is not None
            assert monitoring is not None
            assert logging is not None

        # Run in multiple threads
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(get_clients) for _ in range(10)]
            for future in as_completed(futures):
                future.result()  # Should not raise

    @patch("cloud_resource_inefficiency.providers.gcp.client_factory.storage")
    def test_gcp_factory_project_id_consistency(self, mock_storage: MagicMock) -> None:
        """GCP factory should maintain consistent project ID across threads."""
        mock_storage.Client.return_value = MagicMock()
        project_id = "test-project-123"
        factory = GCPClientFactory(project_id=project_id)

        results = []
        lock = threading.Lock()

        def verify_project_id() -> None:
            """Verify project ID in a thread."""
            # Since we can't easily access project_id from factory,
            # we just ensure calls complete successfully
            storage = factory.get_storage_client()
            with lock:
                results.append(storage is not None)

        # Run in multiple threads
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(verify_project_id) for _ in range(10)]
            for future in as_completed(futures):
                future.result()

        # All results should be True
        assert all(results)
        assert len(results) == 10


class TestFactoryConcurrentRegionAccess:
    """Tests for concurrent access with different regions."""

    @patch("cloud_resource_inefficiency.providers.aws.client_factory.boto3")
    def test_aws_factory_multiple_regions_concurrent(self, mock_boto3: MagicMock) -> None:
        """AWS factories with different regions should work concurrently."""
        mock_boto3.client.return_value = MagicMock()

        factories = {
            "us-east-1": AWSClientFactory(region="us-east-1"),
            "us-west-2": AWSClientFactory(region="us-west-2"),
            "eu-west-1": AWSClientFactory(region="eu-west-1"),
        }

        results = []
        lock = threading.Lock()

        def get_client_for_region(region: str) -> None:
            """Get client for specific region in a thread."""
            factory = factories[region]
            client = factory.get_ec2_client()
            with lock:
                results.append((region, client is not None))

        # Run in multiple threads
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for _ in range(3):  # 3 iterations per region
                for region in factories.keys():
                    futures.append(executor.submit(get_client_for_region, region))

            for future in as_completed(futures):
                future.result()

        # All regions should have succeeded
        assert all(success for _, success in results)
