"""Collector for AWS Elastic Block Store (EBS) volumes."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from cloud_resource_inefficiency.core.enums import CloudProvider, ResourceType
from cloud_resource_inefficiency.core.interfaces import BaseResourceCollector
from cloud_resource_inefficiency.core.models import CloudResource
from cloud_resource_inefficiency.core.resilience import retry
from cloud_resource_inefficiency.providers.aws.client_factory import AWSClientFactory

logger = logging.getLogger(__name__)


class AWSEBSCollector(BaseResourceCollector):
    """Discovers AWS EBS volumes across regions."""

    def __init__(self, client_factory: Optional[AWSClientFactory] = None) -> None:
        self._client_factory = client_factory or AWSClientFactory()

    @property
    def provider(self) -> CloudProvider:
        return CloudProvider.AWS

    @property
    def resource_type(self) -> ResourceType:
        return ResourceType.AWS_EBS_VOLUME

    @retry(max_attempts=3, base_delay=1.0, backoff_factor=2.0)
    def collect(self, region: str, **kwargs: Any) -> List[CloudResource]:
        """Collects EBS volumes in the specified AWS region with retry logic."""
        logger.debug("Starting EBS volume collection in region: %s", region)
        ec2_client = self._client_factory.get_client("ec2", region_name=region)
        paginator = ec2_client.get_paginator("describe_volumes")

        # Optional filters, e.g. status='available' or custom filters passed in kwargs
        filters = kwargs.get("filters", [])
        volume_ids = kwargs.get("volume_ids", [])

        paginate_kwargs: Dict[str, Any] = {}
        if filters:
            paginate_kwargs["Filters"] = filters
        if volume_ids:
            paginate_kwargs["VolumeIds"] = volume_ids

        resources: List[CloudResource] = []

        try:
            for page in paginator.paginate(**paginate_kwargs):
                for vol in page.get("Volumes", []):
                    volume_id = vol.get("VolumeId")
                    tags = {t.get("Key", ""): t.get("Value", "") for t in vol.get("Tags", [])}
                    name = tags.get("Name")
                    created_at = vol.get("CreateTime")
                    status = vol.get("State")

                    # Extract attachments
                    attachments = vol.get("Attachments", [])
                    is_attached = len(attachments) > 0

                    raw_meta = {
                        "size_gib": vol.get("Size"),
                        "volume_type": vol.get("VolumeType"),
                        "iops": vol.get("Iops"),
                        "throughput": vol.get("Throughput"),
                        "availability_zone": vol.get("AvailabilityZone"),
                        "encrypted": vol.get("Encrypted"),
                        "snapshot_id": vol.get("SnapshotId"),
                        "is_attached": is_attached,
                        "attachments": attachments,
                        "multi_attach_enabled": vol.get("MultiAttachEnabled", False),
                    }

                    resource = CloudResource(
                        resource_id=volume_id,
                        name=name,
                        provider=self.provider,
                        resource_type=self.resource_type,
                        region=region,
                        tags=tags,
                        created_at=created_at,
                        status=status,
                        raw_metadata=raw_meta,
                    )
                    resources.append(resource)
                    logger.debug("Discovered EBS volume: %s (status=%s, size=%s GiB)", volume_id, status, raw_meta.get("size_gib"))

            logger.info("Successfully collected %d EBS volumes in region %s", len(resources), region)
        except Exception as e:
            logger.error("Error collecting EBS volumes in region %s: %s", region, str(e), exc_info=True)
            raise RuntimeError(f"Error collecting EBS volumes in region {region}: {e}") from e

        return resources
