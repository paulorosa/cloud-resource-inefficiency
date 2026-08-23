"""Default EBS pricing rates by region and volume type as fallback."""

from typing import Dict

# Default standard AWS EBS rates (USD per GiB-month)
# Based on standard AWS EBS pricing
DEFAULT_EBS_STORAGE_RATES_PER_GIB: Dict[str, Dict[str, float]] = {
    "us-east-1": {
        "gp3": 0.08,
        "gp2": 0.10,
        "io1": 0.125,
        "io2": 0.125,
        "st1": 0.045,
        "sc1": 0.015,
        "standard": 0.05,
    },
    "us-east-2": {
        "gp3": 0.08,
        "gp2": 0.10,
        "io1": 0.125,
        "io2": 0.125,
        "st1": 0.045,
        "sc1": 0.015,
        "standard": 0.05,
    },
    "us-west-2": {
        "gp3": 0.08,
        "gp2": 0.10,
        "io1": 0.125,
        "io2": 0.125,
        "st1": 0.045,
        "sc1": 0.015,
        "standard": 0.05,
    },
    "sa-east-1": {
        "gp3": 0.128,
        "gp2": 0.19,
        "io1": 0.238,
        "io2": 0.238,
        "st1": 0.086,
        "sc1": 0.029,
        "standard": 0.095,
    },
    "eu-west-1": {
        "gp3": 0.088,
        "gp2": 0.11,
        "io1": 0.138,
        "io2": 0.138,
        "st1": 0.05,
        "sc1": 0.017,
        "standard": 0.055,
    },
}

# General fallback if region not explicitly mapped
FALLBACK_STORAGE_RATES: Dict[str, float] = {
    "gp3": 0.08,
    "gp2": 0.10,
    "io1": 0.125,
    "io2": 0.125,
    "st1": 0.045,
    "sc1": 0.015,
    "standard": 0.05,
}

# Provisioned IOPS Rates (USD per IOPS-month)
DEFAULT_IOPS_RATES: Dict[str, Dict[str, float]] = {
    "us-east-1": {
        "gp3": 0.005,      # Provisioned IOPS above baseline 3,000
        "io1": 0.065,      # All provisioned IOPS
        "io2": 0.065,      # Tier 1 (up to 32,000 IOPS)
    },
    "sa-east-1": {
        "gp3": 0.008,
        "io1": 0.124,
        "io2": 0.124,
    }
}

FALLBACK_IOPS_RATES: Dict[str, float] = {
    "gp3": 0.005,
    "io1": 0.065,
    "io2": 0.065,
}

# Provisioned Throughput Rates (USD per MB/s-month)
DEFAULT_THROUGHPUT_RATES: Dict[str, Dict[str, float]] = {
    "us-east-1": {
        "gp3": 0.04,       # Provisioned throughput above baseline 125 MB/s
    },
    "sa-east-1": {
        "gp3": 0.064,
    }
}

FALLBACK_THROUGHPUT_RATES: Dict[str, float] = {
    "gp3": 0.04,
}
