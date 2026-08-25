"""CloudWatch metrics provider for AWS resources."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from cloud_resource_inefficiency.core.enums import CloudProvider
from cloud_resource_inefficiency.core.interfaces import BaseMetricsProvider
from cloud_resource_inefficiency.core.models import CloudResource, MetricSummary
from cloud_resource_inefficiency.providers.aws.client_factory import AWSClientFactory


class AWSCloudWatchMetricsProvider(BaseMetricsProvider):
    """Fetches and aggregates CloudWatch metrics for AWS resources."""

    def __init__(self, client_factory: Optional[AWSClientFactory] = None) -> None:
        self._client_factory = client_factory or AWSClientFactory()

    @property
    def provider(self) -> CloudProvider:
        return CloudProvider.AWS

    def get_metric_summary(
        self,
        resource: CloudResource,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
        statistic: str = "Sum",
        namespace: Optional[str] = None,
        period: int = 86400,  # 1 day intervals by default
        **kwargs: Any
    ) -> MetricSummary:
        """
        Query CloudWatch for metric statistics and return an aggregated summary.
        """
        region = resource.region
        cw_client = self._client_factory.get_client("cloudwatch", region_name=region)

        # Default namespace for EBS
        if not namespace:
            if resource.resource_type.value == "aws_ebs_volume":
                namespace = "AWS/EBS"
            else:
                namespace = "AWS/EC2"

        # Dimensions mapping
        dimensions = []
        if resource.resource_type.value == "aws_ebs_volume":
            dimensions.append({"Name": "VolumeId", "Value": resource.resource_id})
        else:
            dimensions.append({"Name": "InstanceId", "Value": resource.resource_id})

        period_days = max(1, (end_time - start_time).days)

        try:
            response = cw_client.get_metric_statistics(
                Namespace=namespace,
                MetricName=metric_name,
                Dimensions=dimensions,
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=[statistic, "Average", "Maximum"],
            )

            datapoints = response.get("Datapoints", [])
            unit = datapoints[0].get("Unit", "None") if datapoints else "Count"

            if not datapoints:
                return MetricSummary(
                    metric_name=metric_name,
                    unit=unit,
                    period_days=period_days,
                    total_value=0.0,
                    average_value=0.0,
                    maximum_value=0.0,
                    datapoint_count=0,
                    additional_info={"status": "NO_DATA", "namespace": namespace},
                )

            total_val = sum(dp.get(statistic, 0.0) for dp in datapoints)
            max_val = max(dp.get("Maximum", 0.0) for dp in datapoints)
            avg_val = (
                sum(dp.get("Average", 0.0) for dp in datapoints) / len(datapoints)
                if datapoints
                else 0.0
            )

            return MetricSummary(
                metric_name=metric_name,
                unit=unit,
                period_days=period_days,
                total_value=float(total_val),
                average_value=float(avg_val),
                maximum_value=float(max_val),
                datapoint_count=len(datapoints),
                additional_info={"status": "OK", "namespace": namespace, "statistic_used": statistic},
            )

        except Exception as e:
            return MetricSummary(
                metric_name=metric_name,
                unit="None",
                period_days=period_days,
                total_value=0.0,
                average_value=0.0,
                maximum_value=0.0,
                datapoint_count=0,
                additional_info={"status": "ERROR", "error_message": str(e)},
            )
