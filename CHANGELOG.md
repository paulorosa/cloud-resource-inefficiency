# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Semantic Versioning (SemVer)](https://semver.org/lang/pt-BR/).

---

## [Unreleased]
### Added
- Novas regras de ineficiência planejadas (ex: Elastic IPs órfãos, volumes não criptografados, etc.).

---

## [0.1.0] - 2026-08-25
### Added
- **Mecanismo de Detecção**: Implementação da regra `InactiveDetachedEBSVolumeRule` (CER-0066).
- **Coletores de Inventário**: Coletor `AWSEBSCollector` com suporte a paginação e extração de metadados de tags.
- **Provedor de Métricas**: `AWSCloudWatchMetricsProvider` para consulta e agregação de métricas de I/O em janelas configuráveis (padrão: 14 dias).
- **Provedor de Precificação**: `AWSPricingProvider` integrando com a AWS Pricing API (`get_products`) e fallback local estruturado para tipos `gp2`, `gp3`, `io1`, `io2`, `st1`, `sc1`, `standard`, além de IOPS e throughput provisionados adicionais.
- **Formatadores de Saída**: `ScanResultFormatter` com suporte para Texto (Console/ASCII), Markdown renderizável e JSON serializável.
- **Arquitetura Base**: Design baseado em padrões SOLID (Strategy, Registry, DTOs imutáveis com `dataclasses`).
- **Suíte de Testes**: Testes unitários e de integração utilizando mocks (100% isolados de credenciais reais).
