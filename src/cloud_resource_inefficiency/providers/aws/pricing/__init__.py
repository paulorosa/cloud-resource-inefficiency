"""AWS Pricing package."""

from .aws_pricing import AWSPricingProvider
from .default_rates import (
    DEFAULT_EBS_STORAGE_RATES_PER_GIB,
    DEFAULT_IOPS_RATES,
    DEFAULT_THROUGHPUT_RATES,
)

__all__ = [
    "AWSPricingProvider",
    "DEFAULT_EBS_STORAGE_RATES_PER_GIB",
    "DEFAULT_IOPS_RATES",
    "DEFAULT_THROUGHPUT_RATES",
]
