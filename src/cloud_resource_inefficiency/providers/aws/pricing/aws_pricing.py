"""AWS Pricing Provider integrating Price List API and local rate engine."""

import json
import logging
import threading
from typing import Any, Dict, Optional

from cloud_resource_inefficiency.core.enums import CloudProvider, ResourceType
from cloud_resource_inefficiency.core.interfaces import BasePricingProvider
from cloud_resource_inefficiency.core.models import CloudResource, PricingDetails
from cloud_resource_inefficiency.providers.aws.client_factory import AWSClientFactory
from cloud_resource_inefficiency.providers.aws.pricing.default_rates import (
    DEFAULT_EBS_STORAGE_RATES_PER_GIB,
    DEFAULT_IOPS_RATES,
    DEFAULT_THROUGHPUT_RATES,
    FALLBACK_IOPS_RATES,
    FALLBACK_STORAGE_RATES,
    FALLBACK_THROUGHPUT_RATES,
)

logger = logging.getLogger(__name__)


# AWS Region Name to Pricing API Location Name mapping
REGION_TO_LOCATION = {
    "us-east-1": "US East (N. Virginia)",
    "us-east-2": "US East (Ohio)",
    "us-west-1": "US West (N. California)",
    "us-west-2": "US West (Oregon)",
    "sa-east-1": "South America (Sao Paulo)",
    "eu-west-1": "EU (Ireland)",
    "eu-central-1": "EU (Frankfurt)",
    "ap-southeast-1": "Asia Pacific (Singapore)",
    "ap-northeast-1": "Asia Pacific (Tokyo)",
}


class AWSPricingProvider(BasePricingProvider):
    """Calculates resource pricing for AWS using AWS Pricing API with fallback rates."""

    def __init__(
        self,
        client_factory: Optional[AWSClientFactory] = None,
        use_remote_api: bool = True,
    ) -> None:
        self._client_factory = client_factory or AWSClientFactory()
        self._use_remote_api = use_remote_api
        self._pricing_cache: Dict[str, float] = {}
        self._lock = threading.Lock()

    @property
    def provider(self) -> CloudProvider:
        return CloudProvider.AWS

    def get_resource_pricing(self, resource: CloudResource) -> PricingDetails:
        """Calculate estimated monthly pricing for an AWS resource."""
        if resource.resource_type == ResourceType.AWS_EBS_VOLUME:
            return self._calculate_ebs_pricing(resource)
        
        # Generic fallback
        return PricingDetails(
            monthly_cost=0.0,
            currency="USD",
            rate_source="unsupported_resource_type",
        )

    def _calculate_ebs_pricing(self, resource: CloudResource) -> PricingDetails:
        """Calculates monthly pricing for an EBS volume."""
        raw_meta = resource.raw_metadata or {}
        volume_type = str(raw_meta.get("volume_type", "gp3")).lower()
        size_gib = float(raw_meta.get("size_gib", 0.0))
        iops = int(raw_meta.get("iops", 0) or 0)
        throughput = int(raw_meta.get("throughput", 0) or 0)
        region = resource.region

        logger.debug("Calculating pricing for EBS volume %s (type=%s, size=%s GiB, iops=%s, region=%s)",
                     resource.resource_id, volume_type, size_gib, iops, region)

        # 1. Base storage rate ($/GiB-month)
        storage_rate, rate_source = self._get_ebs_storage_rate(region, volume_type)
        storage_cost = size_gib * storage_rate

        # 2. IOPS cost
        iops_cost = 0.0
        iops_rate = self._get_ebs_iops_rate(region, volume_type)
        if volume_type == "gp3":
            # gp3 includes 3,000 IOPS free; bill for excess
            extra_iops = max(0, iops - 3000)
            iops_cost = extra_iops * iops_rate
        elif volume_type in ("io1", "io2"):
            # io1/io2 bills for all provisioned IOPS
            iops_cost = iops * iops_rate

        # 3. Throughput cost
        throughput_cost = 0.0
        throughput_rate = self._get_ebs_throughput_rate(region, volume_type)
        if volume_type == "gp3":
            # gp3 includes 125 MB/s free; bill for excess
            extra_throughput = max(0, throughput - 125)
            throughput_cost = extra_throughput * throughput_rate

        total_monthly = storage_cost + iops_cost + throughput_cost

        logger.info("EBS pricing calculated for %s: total=$%.2f (storage=$%.2f, iops=$%.2f, throughput=$%.2f) from source: %s",
                    resource.resource_id, total_monthly, storage_cost, iops_cost, throughput_cost, rate_source)

        cost_breakdown = {
            "storage_cost": storage_cost,
            "iops_cost": iops_cost,
            "throughput_cost": throughput_cost,
        }

        unit_rates = {
            "storage_rate_per_gib": storage_rate,
            "iops_rate_per_unit": iops_rate,
            "throughput_rate_per_mb_s": throughput_rate,
        }

        return PricingDetails(
            monthly_cost=total_monthly,
            currency="USD",
            rate_source=rate_source,
            unit_rates=unit_rates,
            cost_breakdown=cost_breakdown,
        )

    def _get_ebs_storage_rate(self, region: str, volume_type: str) -> tuple[float, str]:
        """Fetch storage rate from cache, Pricing API, or fallback tables."""
        cache_key = f"ebs_storage:{region}:{volume_type}"
        with self._lock:
            if cache_key in self._pricing_cache:
                return self._pricing_cache[cache_key], "pricing_cache"

        if self._use_remote_api:
            try:
                rate = self._fetch_rate_from_aws_pricing_api(region, volume_type)
                if rate is not None:
                    with self._lock:
                        self._pricing_cache[cache_key] = rate
                    return rate, "aws_pricing_api"
            except Exception as exc:
                logger.debug("Failed to fetch from AWS Pricing API (%s), using default rates: %s", cache_key, exc)

        # Fallback to local default rates
        regional_rates = DEFAULT_EBS_STORAGE_RATES_PER_GIB.get(region, FALLBACK_STORAGE_RATES)
        rate = regional_rates.get(volume_type, FALLBACK_STORAGE_RATES.get(volume_type, 0.10))
        with self._lock:
            self._pricing_cache[cache_key] = rate
        return rate, "default_rates_table"

    def _fetch_rate_from_aws_pricing_api(self, region: str, volume_type: str) -> Optional[float]:
        """Queries the AWS Pricing API in us-east-1 for EBS storage rate."""
        location = REGION_TO_LOCATION.get(region)
        if not location:
            logger.debug("Region %s not found in location mapping, skipping AWS Pricing API call", region)
            return None

        logger.debug("Fetching EBS storage rate from AWS Pricing API for region=%s, volume_type=%s", region, volume_type)
        pricing_client = self._client_factory.get_client("pricing", region_name="us-east-1")
        
        # Mapping volume type to AWS Pricing volume type name
        type_mapping = {
            "gp3": "General Purpose (gp3)",
            "gp2": "General Purpose",
            "io1": "Provisioned IOPS",
            "io2": "Provisioned IOPS (io2)",
            "st1": "Throughput Optimized HDD",
            "sc1": "Cold HDD",
            "standard": "Magnetic",
        }
        api_vol_type = type_mapping.get(volume_type, "General Purpose (gp3)")

        filters = [
            {"Type": "TERM_MATCH", "Field": "ServiceCode", "Value": "AmazonEC2"},
            {"Type": "TERM_MATCH", "Field": "location", "Value": location},
            {"Type": "TERM_MATCH", "Field": "productFamily", "Value": "Storage"},
            {"Type": "TERM_MATCH", "Field": "volumeApiName", "Value": volume_type},
        ]

        try:
            response = pricing_client.get_products(
                ServiceCode="AmazonEC2",
                Filters=filters,
                MaxResults=1,
            )

            price_list = response.get("PriceList", [])
            if not price_list:
                logger.debug("No pricing data found from AWS Pricing API for region=%s, volume_type=%s", region, volume_type)
                return None

            product_data = json.loads(price_list[0]) if isinstance(price_list[0], str) else price_list[0]
            terms = product_data.get("terms", {}).get("OnDemand", {})
            for _, term in terms.items():
                price_dimensions = term.get("priceDimensions", {})
                for _, dim in price_dimensions.items():
                    price_per_unit = dim.get("pricePerUnit", {}).get("USD")
                    if price_per_unit:
                        rate = float(price_per_unit)
                        logger.info("Successfully fetched EBS rate from AWS Pricing API: region=%s, volume_type=%s, rate=$%s", region, volume_type, rate)
                        return rate
        except Exception as e:
            logger.warning("Error fetching from AWS Pricing API: %s", str(e), exc_info=True)

        return None

    def _get_ebs_iops_rate(self, region: str, volume_type: str) -> float:
        regional = DEFAULT_IOPS_RATES.get(region, FALLBACK_IOPS_RATES)
        return regional.get(volume_type, FALLBACK_IOPS_RATES.get(volume_type, 0.0))

    def _get_ebs_throughput_rate(self, region: str, volume_type: str) -> float:
        regional = DEFAULT_THROUGHPUT_RATES.get(region, FALLBACK_THROUGHPUT_RATES)
        return regional.get(volume_type, FALLBACK_THROUGHPUT_RATES.get(volume_type, 0.0))
