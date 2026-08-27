"""Collector for Google Cloud Storage (GCS) buckets."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from google.cloud import storage

from cloud_resource_inefficiency.core.enums import CloudProvider, ResourceType
from cloud_resource_inefficiency.core.interfaces import BaseResourceCollector
from cloud_resource_inefficiency.core.models import CloudResource
from cloud_resource_inefficiency.providers.gcp.client_factory import GCPClientFactory


class GCSCollector(BaseResourceCollector):
    """Discovers Google Cloud Storage buckets."""

    def __init__(self, client_factory: Optional[GCPClientFactory] = None) -> None:
        self._client_factory = client_factory or GCPClientFactory()

    @property
    def provider(self) -> CloudProvider:
        return CloudProvider.GCP

    @property
    def resource_type(self) -> ResourceType:
        return ResourceType.GCP_GCS_BUCKET

    def collect(self, region: str, **kwargs: Any) -> List[CloudResource]:
        """Collects GCS buckets in the GCP project."""
        
        try:
            storage_client = self._client_factory.get_storage_client()
            resources: List[CloudResource] = []
            
            buckets = list(storage_client.list_buckets())
            
            for bucket in buckets:
                bucket_name = bucket.name
                bucket_reload = storage_client.get_bucket(bucket_name)
                
                total_size_bytes = 0
                try:
                    for blob in bucket_reload.list_blobs():
                        total_size_bytes += blob.size or 0
                except Exception:
                    pass
                
                tags = {k: v for k, v in (bucket_reload.labels or {}).items()}
                
                raw_meta = {
                    "location": bucket_reload.location,
                    "storage_class": bucket_reload.storage_class,
                    "size_bytes": total_size_bytes,
                    "size_gib": round(total_size_bytes / (1024 ** 3), 4),
                    "versioning_enabled": bucket_reload.versioning_enabled or False,
                    "lifecycle_rules": sum(1 for _ in (bucket_reload.lifecycle_rules or ())),
                }
                
                resource = CloudResource(
                    resource_id=bucket_name,
                    name=bucket_name,
                    provider=self.provider,
                    resource_type=self.resource_type,
                    region=bucket_reload.location or "global",
                    account_id=bucket_reload.project_number,
                    tags=tags,
                    created_at=bucket_reload.time_created,
                    status="active",
                    raw_metadata=raw_meta,
                )
                resources.append(resource)
        except Exception as e:
            raise RuntimeError(f"Error collecting GCS buckets: {e}") from e

        return resources
