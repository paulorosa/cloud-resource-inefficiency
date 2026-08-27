# Requirements Document: Documentation Refactoring

## Introduction

This document specifies the refactoring of the cloud-resource-inefficiency project documentation to separate provider-specific content into dedicated documentation files while keeping the main README concise (~80 lines) with quick navigation.

## Glossary

- **Main README**: The root `README.md` file that serves as the entry point to the project
- **Provider Docs**: Provider-specific documentation files located in `docs/providers/{provider}/README.md`
- **Provider**: Cloud platform (AWS, GCP, Azure)
- **Inefficiency Rule**: A specific detection rule for a cloud resource (e.g., AWS-EBS-001)
- **Quick Start**: A minimal example showing basic usage to get started quickly
- **ADR**: Architecture Decision Record documents in `/docs/adr` directory

## Requirements

### Requirement 1

**User Story:** As a new user, I want to quickly understand what providers are supported and their main rules, so that I can decide which documentation to read.

#### Acceptance Criteria

1. WHEN a user opens the main README THEN THE main README SHALL display badges (Python version, License) and a clear project description within the first 10 lines
2. WHEN a user scans the main README THEN THE main README SHALL display a provider summary table with links to provider-specific documentation within 30 lines
3. WHEN a user reads the main README THEN THE main README SHALL list supported inefficiency rules with rule IDs grouped by provider within 50 lines

### Requirement 2

**User Story:** As a developer, I want quick-start examples in the main README that link to full examples in the `/examples` folder, so that I can get running without reading all documentation.

#### Acceptance Criteria

1. WHEN a user reads the main README THEN THE main README SHALL include a brief "Quick Start" section showing one simple multi-provider example (5-10 lines of code)
2. WHEN viewing the Quick Start example THEN THE main README SHALL include a link to the `/examples` directory for more complete examples
3. WHEN a user needs installation details THEN THE main README SHALL include a brief installation section with links to provider-specific docs for extended options

### Requirement 3

**User Story:** As an AWS user, I want comprehensive AWS provider documentation covering EBS volume detection, so that I understand criteria, pricing, and remediation for that provider.

#### Acceptance Criteria

1. WHEN a user opens `docs/providers/aws/README.md` THEN THE AWS provider doc SHALL describe the AWS-EBS-001 rule with detection criteria (state, metrics, inactivity threshold)
2. WHEN reading AWS documentation THEN THE AWS doc SHALL document pricing sources (AWS Pricing API and Fallback Rates table)
3. WHEN reviewing the AWS doc THEN THE AWS doc SHALL explain risk assessment logic based on snapshots and retention tags
4. WHEN a user needs to implement AWS scanning THEN THE AWS doc SHALL include complete code examples showing resource collection, metrics analysis, and pricing calculation
5. WHEN a user runs AWS scanning THEN THE AWS doc SHALL show example output formats (text, markdown, JSON) from actual scans

### Requirement 4

**User Story:** As a GCP user, I want comprehensive GCP provider documentation covering GCS bucket detection, so that I understand criteria, pricing, and remediation for that provider.

#### Acceptance Criteria

1. WHEN a user opens `docs/providers/gcp/README.md` THEN THE GCP provider doc SHALL describe the GCP-GCS-001 rule with detection criteria (inactivity period, zero operations, storage classes)
2. WHEN reading GCP documentation THEN THE GCP doc SHALL document the standard pricing table for GCS storage classes (Standard, Nearline, Coldline, Archive)
3. WHEN reviewing the GCP doc THEN THE GCP doc SHALL explain how risk and confidence levels are assigned based on bucket state
4. WHEN a user needs to implement GCP scanning THEN THE GCP doc SHALL include complete code examples for bucket collection, Cloud Logging analysis, and pricing
5. WHEN a user runs GCP scanning THEN THE GCP doc SHALL show example output formats (text, markdown, JSON) from actual scans

### Requirement 5

**User Story:** As an Azure user, I want comprehensive Azure provider documentation covering Managed Disk detection, so that I understand criteria, pricing, and remediation for that provider.

#### Acceptance Criteria

1. WHEN a user opens `docs/providers/azure/README.md` THEN THE Azure provider doc SHALL describe the AZURE-MANAGED-DISK-001 rule with detection criteria (unattached state, metrics, inactivity threshold)
2. WHEN reading Azure documentation THEN THE Azure doc SHALL document the standard pricing table for disk SKUs (Premium, Standard SSD, Standard HDD, Ultra)
3. WHEN reviewing the Azure doc THEN THE Azure doc SHALL explain risk and confidence adjustments based on tags and backup status
4. WHEN a user needs to implement Azure scanning THEN THE Azure doc SHALL include complete code examples for disk collection, Azure Monitor metrics, and pricing
5. WHEN a user runs Azure scanning THEN THE Azure doc SHALL show example output formats (text, markdown, JSON) from actual scans

### Requirement 6

**User Story:** As a maintainer, I want the main README to link to ADRs and examples directory, so that users can explore architectural decisions and additional reference implementations.

#### Acceptance Criteria

1. WHEN a user finishes reading the main README THEN THE main README SHALL include a "Learn More" section with links to `/docs/adr` for architectural decisions
2. WHEN a user wants more examples THEN THE main README SHALL include a link to the `/examples` directory for complete reference implementations
3. WHEN a user reads the footer THEN THE main README SHALL include License information with a link to the LICENSE file

### Requirement 7

**User Story:** As a content maintainer, I want to keep the main README concise while ensuring all provider documentation is complete, so that information is organized logically without duplication.

#### Acceptance Criteria

1. WHEN counting lines in the main README THEN THE main README SHALL contain approximately 80 lines (excluding blank lines for formatting)
2. WHEN reviewing both documents THEN THE main README and provider docs SHALL NOT duplicate content (provider-specific details go to provider docs)
3. WHEN a user reads the main README THEN THE main README SHALL be self-contained for understanding project scope without reading provider docs

