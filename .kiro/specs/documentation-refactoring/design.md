# Design Document: Documentation Refactoring

## Overview

Reorganize the cloud-resource-inefficiency documentation into a hierarchical structure:
1. **Main README.md** (~80 lines): Entry point with provider links, quick start, and navigation
2. **Provider-Specific READMEs**: Complete documentation for each provider in `docs/providers/{provider}/README.md`

The design maintains content completeness while improving navigation and reducing cognitive load on first-time users.

## Architecture

### Document Hierarchy

```
README.md (main entry point)
├── Badges & Description
├── Installation (brief)
├── Supported Providers (table with links)
├── Quick Start Example (5-10 lines)
├── Learn More (links to examples, ADRs, providers)
└── License

docs/providers/
├── aws/
│   └── README.md (AWS-EBS-001 complete documentation)
├── gcp/
│   └── README.md (GCP-GCS-001 complete documentation)
└── azure/
    └── README.md (AZURE-MANAGED-DISK-001 complete documentation)

docs/adr/ (existing ADRs)
examples/ (existing examples)
```

### Main README Structure (80 lines target)

1. **Header Section** (12 lines)
   - Badges (Python 3.9+, License: MIT)
   - Single-line project description
   - Language identifier (English)

2. **Installation Section** (8 lines)
   - Two-option installation (pip, git clone)
   - Note about Azure optional dependencies
   - Link to provider docs for extended options

3. **Supported Providers** (15 lines)
   - Table with provider names, rule IDs, resources
   - Link to each provider's documentation

4. **Inefficiency Rules Summary** (10 lines)
   - Rule ID → Provider + Resource mapping
   - Links to provider docs

5. **Quick Start** (15 lines)
   - One simple Python example (multi-provider scan)
   - Links to `/examples` for complete examples

6. **Learn More Section** (12 lines)
   - Links to `/docs/adr` (architectural decisions)
   - Links to `/examples` (reference implementations)
   - Link to provider documentation

7. **Footer** (8 lines)
   - License link
   - Versioning note
   - Contributing info (optional brief line)

### Provider Documentation Structure

Each provider README follows this structure:

1. **Provider Overview** (5 lines)
   - Provider name and general approach
   - Link back to main README

2. **Inefficiency Rule Details** (20 lines per rule)
   - Rule ID and title
   - Detection criteria (clear, actionable)
   - Risk assessment logic
   - Confidence level calculation

3. **Pricing Information** (15 lines)
   - Pricing sources (API or fallback table)
   - Cost calculation method
   - Example pricing scenarios

4. **Complete Code Examples** (30 lines)
   - Provider-specific imports
   - Scanner initialization
   - Scan execution
   - Result processing and formatting

5. **Example Output** (25 lines)
   - Text format output (table)
   - Markdown format output (table)
   - JSON format output (truncated with details link)

6. **Authentication & Setup** (15 lines)
   - Required credentials/environment variables
   - Region/scope configuration
   - Troubleshooting tips

7. **Testing & Validation** (10 lines)
   - How to run tests for this provider
   - Expected test outcomes
   - Links to test files

8. **Extended Resources** (10 lines)
   - Links to external provider documentation
   - Related ADRs (if any)
   - Migration/upgrade notes

### Content Migration Map

**From main README → to provider docs:**
- AWS-EBS-001 detailed criteria → docs/providers/aws/README.md
- AWS pricing details → docs/providers/aws/README.md
- AWS example code → docs/providers/aws/README.md
- AWS output examples → docs/providers/aws/README.md
- GCP-GCS-001 detailed criteria → docs/providers/gcp/README.md
- GCP pricing details → docs/providers/gcp/README.md
- GCP example code → docs/providers/gcp/README.md
- GCP output examples → docs/providers/gcp/README.md
- Azure-MANAGED-DISK-001 criteria → docs/providers/azure/README.md
- Azure pricing details → docs/providers/azure/README.md
- Azure example code → docs/providers/azure/README.md
- Azure output examples → docs/providers/azure/README.md

**Remaining in main README:**
- Badges and project description
- Installation (brief)
- Provider overview table with links
- Rules summary with links
- One-line quick start guide
- Links to examples, ADRs, providers
- License and version info

## Implementation Approach

### Phase 1: Create Provider Documentation
1. Extract AWS provider section → `docs/providers/aws/README.md`
2. Extract GCP provider section → `docs/providers/gcp/README.md`
3. Extract Azure provider section → `docs/providers/azure/README.md`

Each provider doc is self-contained with:
- Complete detection criteria
- All pricing information
- Full code examples
- Output samples
- Authentication/setup instructions
- Test information

### Phase 2: Refactor Main README
1. Keep badges, description, installation, and links
2. Create provider summary table (15 lines)
3. Add quick start example (10 lines)
4. Add "Learn More" section with links
5. Remove all provider-specific details
6. Verify line count (~80 lines)

### Phase 3: Validation
1. All provider docs have complete information
2. Main README is concise and navigable
3. No critical content is lost
4. Links between documents work correctly

## Technical Considerations

### Markdown Best Practices
- Use relative links between documents: `../aws/README.md`
- Use consistent heading hierarchy (h1 for title, h2 for sections)
- Include table of contents in provider docs if > 100 lines
- Maintain consistent code block syntax highlighting

### Content Organization
- Provider docs should be independently readable
- Main README should direct users to appropriate docs
- No content duplication between main and provider docs
- External links should prefer official provider documentation

### Tooling & Versioning
- No version changes needed (content only)
- setuptools-scm handles versioning automatically
- CHANGELOG.md updated separately if needed
- GitHub workflows not affected

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do.*

### Property 1: Documentation completeness

For any provider supported by the system, the corresponding provider documentation in `docs/providers/{provider}/README.md` SHALL contain all criteria, pricing, examples, and authentication information needed to implement scanning for that provider without referencing the main README.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4, 5.5**

### Property 2: Main README conciseness

The main README SHALL contain exactly the information needed to understand the project and navigate to provider documentation, resulting in approximately 80 lines when line breaks are counted without excessive formatting.

**Validates: Requirements 7.1**

### Property 3: No critical content loss

For any content section from the original main README describing a provider's inefficiency rules, pricing, or examples, that content SHALL be preserved in the corresponding provider documentation without omission of critical details.

**Validates: Requirements 7.2, 7.3**

### Property 4: Navigation completeness

The main README SHALL contain navigation links to all three provider documentation files, and each provider documentation file SHALL contain a link back to the main README.

**Validates: Requirements 1.2, 6.1, 6.2**

### Property 5: Quick start utility

The Quick Start example in the main README SHALL be executable as-is (with valid cloud credentials) and SHALL demonstrate multi-provider scanning without requiring additional setup beyond reading the example.

**Validates: Requirement 2.1, 2.2**

