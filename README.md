# Cloud Resource Inefficiency

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A modern, modular Python library for identifying cost inefficiencies and financial opportunities in multi-cloud resources (AWS, Azure, GCP). Built with SOLID principles, strategy patterns, DTOs, and strict type hints.

## 📦 Installation

```bash
# Basic installation
pip install git+https://github.com/paulorosa/cloud-resource-inefficiency.git

# With Azure support
pip install "cloud-resource-inefficiency[azure]"
```

For development or version-specific installs, see [docs/providers/aws/README.md](docs/providers/aws/README.md#installation).

## 🌍 Supported Providers

| Provider | Rule(s) | Resource Type | Documentation |
|----------|---------|---------------|---------------|
| **AWS** | AWS-EBS-001 | Inactive/Detached EBS Volumes | [AWS Provider Docs](docs/providers/aws/README.md) |
| **GCP** | GCP-GCS-001 | Inactive GCS Buckets | [GCP Provider Docs](docs/providers/gcp/README.md) |
| **Azure** | AZURE-MANAGED-DISK-001 | Inactive/Detached Managed Disks | [Azure Provider Docs](docs/providers/azure/README.md) |

## 💡 Quick Start

```python
from cloud_resource_inefficiency import (
    CloudProvider, InefficiencyScanner, ScanResultFormatter
)

# Scan multiple providers
scanner = InefficiencyScanner(
    providers=[CloudProvider.AWS, CloudProvider.GCP, CloudProvider.AZURE],
    regions=["us-east-1", "global", "eastus"],
)

result = scanner.scan(lookback_days=14)
print(ScanResultFormatter.to_text_summary(result))

for opp in result.opportunities:
    print(f"{opp.rule_id}: ${opp.estimated_monthly_savings:.2f}/mo ({opp.risk_level.value})")
```

## 📚 Documentation

- **[AWS Provider](docs/providers/aws/README.md)** – EBS detection, pricing, remediation
- **[GCP Provider](docs/providers/gcp/README.md)** – GCS detection, pricing, remediation
- **[Azure Provider](docs/providers/azure/README.md)** – Managed Disk detection, pricing, remediation
- **[Architecture Decisions](docs/adr/README.md)** – Design patterns and trade-offs
- **[Examples](examples/)** – Complete working examples

## 📌 Versioning

This project follows [Semantic Versioning](https://semver.org/). Tags are auto-deployed and versions are auto-generated from Git tags. See [CHANGELOG.md](CHANGELOG.md) for release notes.

## 📄 License

MIT License – See [LICENSE](LICENSE) for details.
