"""Google Cloud Monitoring metrics provider for GCS resources."""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from google.cloud import logging_v2

from cloud_resource_inefficiency.core.enums import CloudProvider
from cloud_resource_inefficiency.core.interfaces import BaseMetricsProvider
from cloud_resource_inefficiency.core.models import CloudResource, MetricSummary
from cloud_resource_inefficiency.providers.gcp.client_factory import GCPClientFactory


class GCPMonitoringMetricsProvider(BaseMetricsProvider):
    """Fetches metrics from Google Cloud Logging and Monitoring."""

    def __init__(self, client_factory: Optional[GCPClientFactory] = None) -> None:
        self._client_factory = client_factory or GCPClientFactory()

    @property
    def provider(self) -> CloudProvider:
        return CloudProvider.GCP

    def get_metric_summary(
        self,
        resource: CloudResource,
        metric_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        statistic: str = "Sum",
        **kwargs: Any
    ) -> MetricSummary:
        """Query Cloud Logging for bucket access activity."""
        period_days = max(1, int(kwargs.get("period_days", 30)))
        end_time = end_time or datetime.now(timezone.utc)
        start_time = start_time or end_time - timedelta(days=period_days)
        period_days = max(1, (end_time - start_time).days)
        
        try:
            logging_client = self._client_factory.get_logging_client()
            bucket_name = resource.resource_id
            
            filter_str = (
                f'protoPayload.resourceName=~"buckets/{bucket_name}(/.*)?$" '
                f'AND timestamp>="{start_time.isoformat()}" '
                f'AND timestamp<="{end_time.isoformat()}"'
            )
            
            entries = logging_client.list_entries(filter_=filter_str)
            entry_count = sum(1 for _ in entries)
            total_operations = entry_count
            
        except Exception as e:
            return MetricSummary(
                metric_name=metric_name,
                unit="Count",
                period_days=period_days,
                total_value=0.0,
                average_value=0.0,
                maximum_value=0.0,
                datapoint_count=0,
                additional_info={"status": "ERROR", "error": str(e)},
            )
        
        avg_value = total_operations / max(1, period_days)
        
        return MetricSummary(
            metric_name=metric_name,
            unit="Count",
            period_days=period_days,
            total_value=float(total_operations),
            average_value=avg_value,
            maximum_value=float(total_operations) if total_operations > 0 else 0.0,
            datapoint_count=1,
            additional_info={"status": "SUCCESS", "source": "cloud_logging"},
        )
