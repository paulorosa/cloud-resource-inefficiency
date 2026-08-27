"""Azure Monitor metrics provider for Managed Disks."""

from datetime import datetime
from typing import Any, Optional

from cloud_resource_inefficiency.core.enums import CloudProvider
from cloud_resource_inefficiency.core.interfaces import BaseMetricsProvider
from cloud_resource_inefficiency.core.models import CloudResource, MetricSummary
from cloud_resource_inefficiency.providers.azure.client_factory import AzureClientFactory


class AzureMonitorMetricsProvider(BaseMetricsProvider):
    """Fetches read/write activity from Azure Monitor."""

    def __init__(self, client_factory: Optional[AzureClientFactory] = None) -> None:
        self._client_factory = client_factory or AzureClientFactory()

    @property
    def provider(self) -> CloudProvider:
        return CloudProvider.AZURE

    def get_metric_summary(
        self, resource: CloudResource, metric_name: str, start_time: datetime,
        end_time: datetime, statistic: str = "Sum", **kwargs: Any
    ) -> MetricSummary:
        period_days = max(1, (end_time - start_time).days)
        try:
            response = self._client_factory.get_monitor_client().metrics.list(
                resource.resource_id,
                timespan=f"{start_time.isoformat()}/{end_time.isoformat()}",
                interval="PT1H",
                metricnames=metric_name,
                aggregation=statistic,
            )
            values = []
            for metric in getattr(response, "value", []) or []:
                for timeseries in getattr(metric, "timeseries", []) or []:
                    for data in getattr(timeseries, "data", []) or []:
                        value = getattr(data, statistic.lower(), None)
                        if value is not None:
                            values.append(float(value))
            total = sum(values)
            return MetricSummary(
                metric_name=metric_name, unit="Count", period_days=period_days,
                total_value=total, average_value=total / max(1, len(values)),
                maximum_value=max(values, default=0.0), datapoint_count=len(values),
                additional_info={"status": "OK" if values else "NO_DATA", "source": "azure_monitor"},
            )
        except Exception as exc:
            return MetricSummary(
                metric_name=metric_name, unit="Count", period_days=period_days,
                total_value=0.0, average_value=0.0, maximum_value=0.0, datapoint_count=0,
                additional_info={"status": "ERROR", "error_message": str(exc)},
            )