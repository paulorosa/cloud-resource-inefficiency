# Architecture Decision Records (ADRs)

Este diretório contém todos os Architecture Decision Records (ADRs) do projeto `cloud-resource-inefficiency`. Os ADRs documentam decisões arquiteturais significativas, o contexto em que foram tomadas, as alternativas consideradas e as consequências resultantes.

## Formato

Os ADRs seguem o padrão **MADR v2.2.0** (Markdown Architecture Decision Records):

- **Status**: Estado atual da decisão (Proposed, Accepted, Deprecated, Superseded)
- **Context**: Problema ou situação que motivou a decisão
- **Decision**: A decisão específica tomada
- **Rationale**: Justificativa para a decisão escolhida
- **Consequences**: Impactos positivos e negativos da decisão
- **Alternatives Considered**: Alternativas avaliadas e por que foram rejeitadas
- **Related Decisions**: Ligações entre ADRs relacionados

## Índice de ADRs

| ADR | Título | Status | Data |
|-----|--------|--------|------|
| [ADR-0001](ADR-0001-multi-provider-architecture.md) | Multi-Provider Architecture with Strategy Pattern | Accepted | 2026-08-25 |
| [ADR-0002](ADR-0002-registry-based-component-management.md) | Registry-Based Component Management | Accepted | 2026-08-25 |
| [ADR-0003](ADR-0003-immutable-data-transfer-objects.md) | Immutable Data Transfer Objects with Dataclasses | Accepted | 2026-08-25 |
| [ADR-0004](ADR-0004-async-first-metrics-collection.md) | Async-First Metrics Collection Strategy | Accepted | 2026-08-25 |
| [ADR-0005](ADR-0005-caching-strategy.md) | Caching Strategy for Pricing and Metrics | Accepted | 2026-08-25 |
| [ADR-0006](ADR-0006-resilience-retry-circuit-breaker.md) | Resilience with Retry and Circuit Breaker | Accepted | 2026-08-25 |
| [ADR-0007](ADR-0007-centralized-logging-configuration.md) | Centralized Logging and Configuration | Accepted | 2026-08-25 |
| [ADR-0008](ADR-0008-rule-evaluation-model.md) | Rule Evaluation Model - Opportunity Detection | Accepted | 2026-08-25 |
| [ADR-0009](ADR-0009-multi-format-output.md) | Multi-Format Output for Scan Results | Accepted | 2026-08-25 |
| [ADR-0010](ADR-0010-python-type-hints.md) | Python 3.9+ with Type Hints | Accepted | 2026-08-25 |
| [ADR-0011](ADR-0011-thread-safe-client-factories.md) | Thread-Safe Client Factories with Lazy Initialization | Accepted | 2026-08-25 |
| [ADR-0012](ADR-0012-optional-azure-support.md) | Optional Azure Support via Extras | Accepted | 2026-08-25 |
| [ADR-0013](ADR-0013-semantic-versioning.md) | Semantic Versioning with setuptools-scm | Accepted | 2026-08-25 |
| [ADR-0014](ADR-0014-github-actions-cicd.md) | GitHub Actions for CI/CD | Accepted | 2026-08-25 |
| [ADR-0015](ADR-0015-property-based-testing.md) | Property-Based Testing for Edge Cases | Accepted | 2026-08-25 |

## Como Usar Este Diretório

1. **Consultando uma Decisão**: Abra o arquivo ADR correspondente (ex: `ADR-0001-*.md`)
2. **Entendendo Relações**: Consulte a seção "Related Decisions" para ver como as decisões se conectam
3. **Propondo Novas Decisões**: Crie um novo ADR seguindo o formato MADR com o próximo número sequencial
4. **Atualizando Status**: Quando uma decisão mudar de status (ex: de Proposed para Accepted), atualize o arquivo correspondente

## Estrutura de Dependências

```
ADR-0001 (Multi-Provider)
├── ADR-0002 (Registry) ←─ Implementa o padrão Strategy
├── ADR-0003 (DTOs) ←─────── Estruturas de dados
└── ADR-0011 (Client Factories) ←─ Criação de clientes

ADR-0007 (Logging/Config)
├── ADR-0005 (Caching)
└── ADR-0006 (Resilience)

ADR-0004 (Async-First)
└── ADR-0005 (Caching)

ADR-0008 (Rule Evaluation)
├── ADR-0001 (Multi-Provider)
└── ADR-0002 (Registry)

ADR-0009 (Output Formats)
└── ADR-0008 (Rule Evaluation)

ADR-0010 (Type Hints)
├── ADR-0003 (DTOs)
└── ADR-0015 (Property-Based Testing)

ADR-0013 (Semantic Versioning)
└── ADR-0014 (GitHub Actions)
```

## Padrões Arquiteturais Implementados

### 1. Strategy Pattern
Implementado em `BaseResourceCollector`, `BaseMetricsProvider`, `BasePricingProvider` para permitir múltiplos provedores cloud (ADR-0001).

### 2. Registry Pattern
Central `InefficiencyRegistry` para auto-descoberta e registro de componentes (ADR-0002).

### 3. Data Transfer Objects (DTOs)
Modelos imutáveis usando `@dataclass` com `frozen=True` (ADR-0003).

### 4. Lazy Initialization
Client factories com criação sob demanda e cache thread-safe (ADR-0011).

### 5. Circuit Breaker
Proteção contra falhas em cascata em chamadas a APIs cloud (ADR-0006).

## Referências

- [MADR v2.2.0](https://adr.github.io/madr/)
- [Semantic Versioning](https://semver.org/lang/pt-BR/)
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)
- [Python Type Hints PEP 484](https://www.python.org/dev/peps/pep-0484/)

## Histórico de Mudanças

- **2026-08-25**: Criação do ADR Index com 15 ADRs iniciais

---

*Última atualização: 2026-08-25*
