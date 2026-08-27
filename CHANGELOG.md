# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Semantic Versioning (SemVer)](https://semver.org/lang/pt-BR/).

---

## [Unreleased]
### Added
- **Provedor Azure**: Suporte a Azure Managed Disks com auto-registro no `InefficiencyScanner`.
- **Detector de Managed Disks inativos e desacoplados**: Implementação da regra `InactiveDetachedManagedDiskRule` (`AZURE-MANAGED-DISK-001`) para identificar discos sem VM associada e sem operações recentes de leitura ou escrita.
- **Coletor Azure Managed Disk**: Descoberta de discos, localização, SKU, tamanho, IOPS, throughput, tags, snapshot e vínculo com VM.
- **Provedor de Métricas Azure**: `AzureMonitorMetricsProvider` para consultar operações de leitura e escrita em uma janela configurável (padrão: 14 dias).
- **Provedor de Precificação Azure**: `AzurePricingProvider` com tarifas padrão por SKU e cálculo baseado no tamanho provisionado.
- **Client Factory Azure**: `AzureClientFactory` com criação lazy e cache de clientes Compute e Monitor usando `DefaultAzureCredential`.
- **Testes Azure**: Cobertura unitária para coleta, registro, pricing e detecção de discos anexados, ativos e inativos.
### Changed
- **Dependências**: Adicionadas dependências opcionais `azure-identity`, `azure-mgmt-compute` e `azure-mgmt-monitor` no extra `azure`.
- **Documentação**: README atualizado com a oportunidade Azure, instalação, exemplo de uso e guia de extensão.

---

## [0.2.1] - 2026-08-26
### Added
- Novas regras de ineficiência planejadas (ex: Elastic IPs órfãos, volumes não criptografados, Persistent Disks inativos, etc.).
### Changed
- **Documentação GCP**: Adicionado ao README um resultado real de execução do `ResourceType.GCP_GCS_BUCKET`, com a detecção `GCP-GCS-001` e economia mensal estimada de $0.50 USD.

---

## [0.2.0] - 2026-08-25
### Added
- **Provedor GCP**: Suporte completo para Google Cloud Platform com auto-registro no `InefficiencyScanner`.
- **Detector de GCS Inativos**: Implementação da regra `InactiveGCSBucketRule` (GCP-GCS-001) para identificar buckets Google Cloud Storage sem atividade (zero read/write ops) ou vazios.
- **Coletor GCS**: `GCSCollector` que descobre buckets GCS, calcula tamanho total de armazenamento por bucket e extrai metadados (localização, classe de storage, labels, lifecycle rules).
- **Provedor de Métricas GCP**: `GCPMonitoringMetricsProvider` que consulta Cloud Logging para determinar atividade de acesso em janela configurável (padrão: 30 dias).
- **Provedor de Precificação GCP**: `GCPPricingProvider` com suporte a classes de storage (Standard, Nearline, Coldline, Archive) com tabelas de preços padrão.
- **Client Factory GCP**: `GCPClientFactory` com gerenciamento de clientes Google Cloud (Storage, Logging, Monitoring) utilizando Application Default Credentials (ADC).
- **Auto-Registro de Provedores**: Atualização do `InefficiencyScanner` para auto-registrar GCP provider junto com AWS.
### Changed
- **Dependências**: Adicionadas `google-cloud-storage>=2.0`, `google-cloud-logging>=3.0`, `google-cloud-monitoring>=2.0` ao `pyproject.toml`.
- **Documentação**: Atualização completa do README.md com exemplos multi-provedor e casos de uso GCP.
### Security
- **Autenticação GCP**: Suporte a Application Default Credentials (ADC) com fallback automático sem exigir credenciais explícitas em código.
- **Isolamento de Clientes**: Thread-safety para gerenciamento de instâncias de clientes GCP com `threading.Lock`.

---

## [0.1.0] - 2026-08-25
### Added
- **Mecanismo de Detecção**: Implementação da regra `InactiveDetachedEBSVolumeRule` (AWS-EBS-001).
- **Coletores de Inventário**: Coletor `AWSEBSCollector` com suporte a paginação e extração de metadados de tags.
- **Provedor de Métricas**: `AWSCloudWatchMetricsProvider` para consulta e agregação de métricas de I/O em janelas configuráveis (padrão: 14 dias).
- **Provedor de Precificação**: `AWSPricingProvider` integrando com a AWS Pricing API (`get_products`) e fallback local estruturado para tipos `gp2`, `gp3`, `io1`, `io2`, `st1`, `sc1`, `standard`, além de IOPS e throughput provisionados adicionais.
- **Formatadores de Saída**: `ScanResultFormatter` com suporte para Texto (Console/ASCII), Markdown renderizável e JSON serializável.
- **Arquitetura Base**: Design baseado em padrões SOLID (Strategy, Registry, DTOs imutáveis com `dataclasses`).
- **Suíte de Testes**: Testes unitários e de integração utilizando mocks (100% isolados de credenciais reais).
### Security
- **Defesa contra Falsos Positivos de Deleção**: `InactiveDetachedEBSVolumeRule` agora aborta a sugestão de deleção se as métricas do CloudWatch falharem com erro de permissão ou timeout.
- **Sanitização de Saída Markdown**: Prevenção de quebra de layout e injeção de HTML/Markdown no formatador de relatórios.
- **Sanitização de Comandos CLI**: Validação estrita de IDs e regiões para evitar injeção de parâmetros nos comandos de remediação.
- **Thread-Safety**: Proteção de concorrência com `threading.Lock` nos caches de instâncias de clientes boto3 e tabelas de precificação.
