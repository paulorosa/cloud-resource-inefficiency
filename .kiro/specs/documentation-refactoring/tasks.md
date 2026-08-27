# Implementation Plan: Documentation Refactoring

## Overview

Refactor the cloud-resource-inefficiency documentation by separating provider-specific content into dedicated README files in `docs/providers/{provider}/` while keeping the main README concise (~80 lines). This improves navigation, reduces cognitive load, and makes the documentation more maintainable.

## Tasks

- [x] 1. Create AWS Provider Documentation
  - [x] 1.1 Extract AWS-EBS-001 rule details and create `docs/providers/aws/README.md`
    - Copy all AWS-EBS-001 detection criteria (state, CloudWatch metrics, inactivity logic)
    - Include complete AWS pricing information (AWS Pricing API + Fallback Rates table)
    - Document risk level and confidence level logic based on snapshots and retention tags
    - Include all AWS example code (scanner initialization, metrics analysis, output formatting)
    - Include example output (text table, markdown table, JSON payload)
    - Document Azure Monitor authentication requirements and troubleshooting
    - Add links to AWS documentation and related tests
    - Add back-link to main README
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 2. Create GCP Provider Documentation
  - [x] 2.1 Extract GCP-GCS-001 rule details and create `docs/providers/gcp/README.md`
    - Copy all GCP-GCS-001 detection criteria (Cloud Logging, zero operations, inactivity window)
    - Include complete GCP pricing table (Standard, Nearline, Coldline, Archive storage classes)
    - Document risk and confidence level assignment logic
    - Include all GCP example code (GCSCollector, Cloud Logging metrics, pricing calculation)
    - Include example output (text table, markdown table, JSON payload)
    - Document GCP authentication requirements (Application Default Credentials)
    - Add links to GCP documentation and related tests
    - Add back-link to main README
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 3. Create Azure Provider Documentation
  - [x] 3.1 Extract Azure Managed Disk rule details and create `docs/providers/azure/README.md`
    - Copy all AZURE-MANAGED-DISK-001 detection criteria (unattached state, Azure Monitor metrics, inactivity threshold)
    - Include complete Azure pricing table by SKU (Premium, Standard SSD, Standard HDD, Ultra)
    - Document risk and confidence adjustments based on tags (retention, backup, migration)
    - Include all Azure example code (AzureClientFactory, Azure Monitor metrics, pricing)
    - Include example output (text table, markdown table, JSON payload)
    - Document Azure authentication requirements (DefaultAzureCredential, subscription selection)
    - Include note about optional Azure dependencies (`pip install "cloud-resource-inefficiency[azure]"`)
    - Add links to Azure documentation and related tests
    - Add back-link to main README
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 4. Refactor Main README to be Concise
  - [x] 4.1 Refactor `README.md` main sections
    - Keep badges (Python 3.9+, License: MIT) in header (2 lines)
    - Keep one-line project description (1 line)
    - Replace full installation section with brief version (3 lines) + link to provider docs
    - Remove all provider-specific criteria details
    - Remove all provider-specific pricing details
    - Remove all extended code examples (keep only 1 quick-start example, 8-10 lines)
    - Remove all extended output examples
    - _Requirements: 1.1, 2.1, 2.3_
  
  - [x] 4.2 Add provider summary table and quick navigation
    - Create table with Provider | Rule ID | Resource | Link columns
    - Table should list AWS-EBS-001, GCP-GCS-001, AZURE-MANAGED-DISK-001 (15 lines total)
    - Add "Quick Start" section with one multi-provider example (8-10 lines)
    - Add link to `/examples` directory for full examples (1 line)
    - _Requirements: 1.2, 1.3, 2.1, 2.2_
  
  - [x] 4.3 Add "Learn More" section and footer
    - Add section linking to `/docs/adr` for architectural decisions (2 lines)
    - Add section linking to `/examples` for reference implementations (1 line)
    - Add section linking to provider documentation (1 line)
    - Add License and versioning footer (3 lines)
    - _Requirements: 6.1, 6.2, 6.3_
  
  - [x] 4.4 Verify main README line count and content completeness
    - Count lines in refactored README.md (target: ~80 lines)
    - Verify no critical information is missing
    - Verify all links are functional and relative
    - Ensure formatting consistency with GitHub markdown style
    - _Requirements: 7.1, 7.2, 7.3_

- [x] 5. Validation and Cross-Document Linking
  - [x] 5.1 Validate all provider documentation files
    - Verify each provider README exists at correct path
    - Verify each provider README contains all required sections
    - Verify no provider-specific content exists in main README
    - Verify no duplication between main and provider docs
    - _Requirements: 3.1, 4.1, 5.1, 7.2_
  
  - [x] 5.2 Verify cross-document linking
    - Test all links from main README to provider docs
    - Test all back-links from provider docs to main README
    - Test links to `/docs/adr` directory
    - Test links to `/examples` directory
    - Verify relative links work correctly in GitHub rendering
    - _Requirements: 1.2, 6.1, 6.2_

- [x] 6. Final Checkpoint - Ensure Documentation is Complete
  - Verify all 4 README files (main + 3 providers) exist and render correctly in GitHub
  - Confirm main README is ~80 lines
  - Confirm each provider README has complete content
  - Confirm all navigation links work
  - Ask the user if questions arise

## Notes

- All file operations are content migrations (copy, move, reformat)
- No code changes needed; this is documentation-only
- Ensure relative links work by using proper markdown link syntax: `[text](../provider/README.md)`
- GitHub renders markdown relative links correctly; test by pushing to branch
- Tasks are sequential but independent subsections can be worked in parallel (e.g., creating all 3 provider docs together)
- Line count in main README is approximate; formatting/readability takes precedence over exact 80-line target

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1", "3.1"] },
    { "id": 1, "tasks": ["4.1", "4.2", "4.3"] },
    { "id": 2, "tasks": ["4.4", "5.1", "5.2"] }
  ]
}
```

