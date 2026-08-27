"""Collector for Azure Managed Disks."""

from typing import Any, List, Optional

from cloud_resource_inefficiency.core.enums import CloudProvider, ResourceType
from cloud_resource_inefficiency.core.interfaces import BaseResourceCollector
from cloud_resource_inefficiency.core.models import CloudResource
from cloud_resource_inefficiency.providers.azure.client_factory import AzureClientFactory


class AzureManagedDiskCollector(BaseResourceCollector):
    """Discovers managed disks in an Azure subscription."""

    def __init__(self, client_factory: Optional[AzureClientFactory] = None) -> None:
        self._client_factory = client_factory or AzureClientFactory()

    @property
    def provider(self) -> CloudProvider:
        return CloudProvider.AZURE

    @property
    def resource_type(self) -> ResourceType:
        return ResourceType.AZURE_MANAGED_DISK

    def collect(self, region: str, **kwargs: Any) -> List[CloudResource]:
        try:
            disks = self._client_factory.get_compute_client().disks.list()
            resources: List[CloudResource] = []
            for disk in disks:
                location = getattr(disk, "location", None) or "global"
                if region and region not in ("*", "all") and location.lower() != region.lower():
                    continue
                properties = getattr(disk, "disk_iops_read_write", None)
                is_attached = bool(getattr(disk, "managed_by", None))
                resource_id = str(getattr(disk, "id", ""))
                disk_name = getattr(disk, "name", None) or resource_id.rsplit("/", 1)[-1]
                resources.append(CloudResource(
                    resource_id=resource_id,
                    name=disk_name,
                    provider=self.provider,
                    resource_type=self.resource_type,
                    region=location,
                    account_id=getattr(self._client_factory, "subscription_id", None),
                    tags=dict(getattr(disk, "tags", None) or {}),
                    created_at=getattr(disk, "time_created", None),
                    status="attached" if is_attached else "unattached",
                    raw_metadata={
                        "size_gib": getattr(disk, "disk_size_gb", None) or 0,
                        "sku": getattr(getattr(disk, "sku", None), "name", None) or "Standard_LRS",
                        "iops": properties or 0,
                        "throughput": getattr(disk, "disk_m_bps_read_write", None) or 0,
                        "is_attached": is_attached,
                        "managed_by": getattr(disk, "managed_by", None),
                        "os_type": getattr(disk, "os_type", None),
                        "hyper_v_generation": getattr(disk, "hyper_v_generation", None),
                    },
                ))
            return resources
        except Exception as exc:
            raise RuntimeError(f"Error collecting Azure Managed Disks in region {region}: {exc}") from exc