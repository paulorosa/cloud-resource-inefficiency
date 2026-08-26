# Cloud Resource Inefficiency (`cloud-resource-inefficiency`)

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Uma biblioteca Python moderna, modular e extensível para **identificação de oportunidades financeiras e ineficiências de custo em recursos de nuvem multi-provedor** (AWS, Azure, GCP).

Desenvolvida seguindo os princípios **SOLID**, padrões de projeto Orientados a Objetos (**Strategy**, **Registry**, **DTOs** e injeção de dependências) e tipagem estrita com `dataclasses`.

---

## 🎯 Oportunidades Implementadas

### 1. Inactive and Detached EBS Volume (AWS-EBS-001)
- **Provedor**: AWS
- **Recurso**: AWS EBS Volume (`aws_ebs_volume`)
- **Categoria**: `Unattached Storage`
- **Critérios de Detecção**:
  - Estado `available` (sem instâncias EC2 anexadas).
  - Análise de métricas do **CloudWatch** (`VolumeReadOps`, `VolumeWriteOps`, `VolumeReadBytes`, `VolumeWriteBytes`) em uma janela de observação (padrão: 14 dias).
  - Inativo se $I/O = 0$.
- **Fontes de Precificação**:
  - **AWS Pricing API** (`get_products` em `us-east-1` com cache em memória).
  - **Tabela de Tarifas Padrão (Fallback)** com suporte a volumes `gp2`, `gp3`, `io1`, `io2`, `st1`, `sc1`, `standard`, além de IOPS e throughput provisionados adicionais.
- **Retorno da Oportunidade**:
  - Economia mensal estimada ($ USD / mês).
  - Nível de risco (`LOW`, `MEDIUM`, `HIGH`) baseado na presença de snapshots recentes e tags de retenção (`DoNotDelete`, `Backup`).
  - Nível de confiança (`HIGH`, `MEDIUM`, `LOW`).
  - Ações recomendadas e comando CLI para remediação segura (`aws ec2 delete-volume ...`).

### 2. Inactive GCS Bucket (GCP-GCS-001)
- **Provedor**: GCP
- **Recurso**: Google Cloud Storage Bucket (`gcp_gcs_bucket`)
- **Categoria**: `Unused Resource`
- **Critérios de Detecção**:
  - Zero operações de leitura/escrita nos últimos **30 dias** (consultando Cloud Logging).
  - OU bucket vazio (0 bytes de armazenamento).
- **Fontes de Precificação**:
  - **Tabela de Tarifas Padrão** com suporte a classes de storage:
    - Standard: $0.020/GB-mês
    - Nearline: $0.010/GB-mês
    - Coldline: $0.004/GB-mês
    - Archive: $0.0036/GB-mês
- **Retorno da Oportunidade**:
  - Economia mensal estimada ($ USD / mês) baseada em custo de armazenamento.
  - Nível de risco (`VERY_LOW` para vazios, `LOW` para inativos).
  - Nível de confiança (`HIGH` ou `MEDIUM`).
  - Ações recomendadas e comando CLI para remediação (`gsutil -m rm -r gs://bucket-name`).

---

## 📦 Como Usar em Outros Projetos (`requirements.txt`)

Para utilizar esta biblioteca em qualquer outro projeto Python, basta adicioná-la diretamente ao arquivo `requirements.txt` do seu projeto consumidor.

### 1. No arquivo `requirements.txt` do seu projeto:

```text
# Opção A: Instalar a versão mais recente da branch main (via HTTPS)
git+https://github.com/paulorosa/cloud-resource-inefficiency.git

# Opção B (Recomendada para Produção): Fixar em uma tag ou versão específica
git+https://github.com/paulorosa/cloud-resource-inefficiency.git@v0.1.0

# Opção C: Usando SSH (para repositórios privados com chave SSH)
git+ssh://git@github.com/paulorosa/cloud-resource-inefficiency.git

# Opção D: Desenvolvimento local em modo editável (mesma máquina)
-e ../cloud-resource-inefficiency
```

### 2. No terminal do projeto consumidor:

```bash
pip install -r requirements.txt
```

---

## 🚀 Instalação Direta via CLI (Opcional)

Se preferir instalar diretamente no ambiente virtual sem usar `requirements.txt`:

```bash
# Instalação direta do repositório remoto
pip install git+https://github.com/paulorosa/cloud-resource-inefficiency.git

# Ou clonando localmente
git clone https://github.com/paulorosa/cloud-resource-inefficiency.git
cd cloud-resource-inefficiency
pip install -e .
```

---

## 💡 Guia de Uso Rápido

### Exemplo em Python - AWS:

```python
from cloud_resource_inefficiency import (
    CloudProvider,
    InefficiencyScanner,
    ResourceType,
    ScanResultFormatter,
)

# 1. Instanciar o scanner com AWS
scanner = InefficiencyScanner(
    providers=[CloudProvider.AWS],
    regions=["us-east-1", "sa-east-1"],
)

# 2. Executar o scan de ineficiências
result = scanner.scan(
    resource_types=[ResourceType.AWS_EBS_VOLUME],
    lookback_days=14,
)

# 3. Exibir resumo em texto no console
print(ScanResultFormatter.to_text_summary(result))

# 4. Acessar os detalhes de cada oportunidade financeira
for opp in result.opportunities:
    print(f"Oportunidade [{opp.rule_id}]: {opp.title}")
    print(f"  Recurso: {opp.resource.resource_id} (Região: {opp.resource.region})")
    print(f"  Economia Estimada: ${opp.estimated_monthly_savings:.2f} USD/mês")
    print(f"  Risco: {opp.risk_level.value} | Confiança: {opp.confidence_level.value}")
    print(f"  Comando de Remediação: {opp.remediation_command}")
```

### Exemplo em Python - GCP:

```python
from cloud_resource_inefficiency import (
    CloudProvider,
    InefficiencyScanner,
    ResourceType,
    ScanResultFormatter,
)

# 1. Instanciar o scanner com GCP
# Nota: Requer autenticação GCP via Application Default Credentials (ADC)
# Configure com: gcloud auth application-default login
scanner = InefficiencyScanner(
    providers=[CloudProvider.GCP],
    regions=["global"],  # GCS é global, mas aceita "global" como região
)

# 2. Executar o scan de ineficiências
result = scanner.scan(
    resource_types=[ResourceType.GCP_GCS_BUCKET],
    lookback_days=30,  # 30 dias para GCS
)

# 3. Exibir resumo em texto no console
print(ScanResultFormatter.to_text_summary(result))

# 4. Acessar os detalhes
for opp in result.opportunities:
    print(f"Oportunidade [{opp.rule_id}]: {opp.title}")
    print(f"  Bucket: {opp.resource.resource_id}")
    print(f"  Economia Estimada: ${opp.estimated_monthly_savings:.2f} USD/mês")
    print(f"  Risco: {opp.risk_level.value} | Confiança: {opp.confidence_level.value}")
```

### Exemplo Multi-Provedor:

```python
from cloud_resource_inefficiency import (
    CloudProvider,
    InefficiencyScanner,
    ScanResultFormatter,
)

# Scan simultâneo em AWS e GCP
scanner = InefficiencyScanner(
    providers=[CloudProvider.AWS, CloudProvider.GCP],
    regions=["us-east-1", "global"],
)

result = scanner.scan(lookback_days=14)
print(ScanResultFormatter.to_markdown(result))
```

### Formatos de Exportação:
- `ScanResultFormatter.to_text_summary(result)`: Tabela formatada para terminal.
- `ScanResultFormatter.to_markdown(result)`: Relatório completo em Markdown.
- `ScanResultFormatter.to_json(result)`: Payload JSON estruturado para integrações ou pipelines CI/CD.
- `ScanResultFormatter.to_dict(result)`: Dicionário Python serializável.

---

## 📊 Exemplo de Saída da Execução

Ao executar o scanner em uma conta com recursos ociosos, o `cloud-resource-inefficiency` disponibiliza múltiplos formatos de saída:

### 1. Resumo em Texto (Terminal / Logs)

```text
======================================================================
               CLOUD FINANCIAL INEFFICIENCY SCAN REPORT
======================================================================
Total Scanned Resources: 15
Opportunities Found:     3
Total Monthly Savings:   $102.40 USD
Annual Projected Saving: $1,228.80 USD
----------------------------------------------------------------------
Rule ID    | Resource ID            | Region       | Savings/Mo   | Risk    
----------------------------------------------------------------------
AWS-EBS-001| vol-0123456789abcdef0  | us-east-1    | $    48.00   | LOW     
AWS-EBS-001| vol-0987654321fedcba1  | sa-east-1    | $    27.20   | MEDIUM  
GCP-GCS-001| old-data-bucket        | global       | $    27.20   | VERY_LOW
======================================================================
```

### 2. Relatório Renderizado (Markdown)

| Rule | Resource ID | Name | Region | Monthly Savings | Risk Level | Confidence | Action |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `AWS-EBS-001` | `vol-0123456789abcdef0` | `app-legacy-temp` | `us-east-1` | **$48.00** | LOW | HIGH | Create snapshot and delete detached volume |
| `AWS-EBS-001` | `vol-0987654321fedcba1` | `db-backup-old` | `sa-east-1` | **$27.20** | MEDIUM | HIGH | Verify retention tags before deletion |
| `GCP-GCS-001` | `old-data-bucket` | `old-data-bucket` | `global` | **$27.20** | VERY_LOW | HIGH | Delete empty bucket immediately |

---

### 3. Payload JSON (Para pipelines CI/CD e automações)

<details>
<summary>👉 Clique aqui para ver o JSON estruturado retornado</summary>

```json
{
  "summary": {
    "total_opportunities": 3,
    "scanned_resources_count": 15,
    "total_estimated_monthly_savings": 102.40,
    "currency": "USD",
    "start_time": "2026-08-25T20:00:00+00:00",
    "end_time": "2026-08-25T20:05:30+00:00",
    "errors_count": 0
  },
  "opportunities": [
    {
      "opportunity_id": "opp-9f3a1b2c",
      "rule_id": "AWS-EBS-001",
      "title": "Inactive and Detached EBS Volume",
      "estimated_monthly_savings": 48.00,
      "currency": "USD",
      "risk_level": "LOW",
      "confidence_level": "HIGH",
      "resource": {
        "resource_id": "vol-0123456789abcdef0",
        "resource_type": "aws_ebs_volume",
        "provider": "aws",
        "region": "us-east-1"
      },
      "remediation_command": "aws ec2 delete-volume --volume-id vol-0123456789abcdef0 --region us-east-1"
    },
    {
      "opportunity_id": "opp-7d4e2f5a",
      "rule_id": "GCP-GCS-001",
      "title": "Inactive GCS Bucket",
      "estimated_monthly_savings": 27.20,
      "currency": "USD",
      "risk_level": "VERY_LOW",
      "confidence_level": "HIGH",
      "resource": {
        "resource_id": "old-data-bucket",
        "resource_type": "gcp_gcs_bucket",
        "provider": "gcp",
        "region": "global"
      },
      "remediation_command": "gsutil -m rm -r gs://old-data-bucket"
    }
  ]
}
```

</details>

---

## 🏗️ Estrutura de Arquitetura

```text
src/cloud_resource_inefficiency/
├── core/                      # Interfaces abstratas, enums e modelos DTO
│   ├── enums.py               # CloudProvider, ResourceType, RiskLevel, ConfidenceLevel
│   ├── models.py              # CloudResource, Opportunity, PricingDetails, ScanResult
│   ├── interfaces.py          # BaseResourceCollector, BaseMetricsProvider, BasePricingProvider
│   ├── rule.py                # BaseInefficiencyRule
│   └── registry.py            # InefficiencyRegistry
├── providers/                 # Provedores de Nuvem
│   ├── aws/
│   │   ├── client_factory.py  # Gerenciador de clientes boto3
│   │   ├── collectors/        # Coleta de inventário (AWSEBSCollector)
│   │   ├── metrics/           # CloudWatch (AWSCloudWatchMetricsProvider)
│   │   ├── pricing/           # AWS Pricing API + Fallback Rates (AWSPricingProvider)
│   │   └── rules/             # Regras de detecção (InactiveDetachedEBSVolumeRule)
│   └── gcp/
│       ├── client_factory.py  # Gerenciador de clientes Google Cloud
│       ├── collectors/        # Coleta de buckets GCS (GCSCollector)
│       ├── metrics/           # Cloud Monitoring/Logging (GCPMonitoringMetricsProvider)
│       ├── pricing/           # GCS Pricing (GCPPricingProvider)
│       └── rules/             # Regras de detecção (InactiveGCSBucketRule)
├── engine/
│   └── scanner.py             # Motor InefficiencyScanner com auto-registro de provedores
└── formatters/
    └── output.py              # Formatadores de saída (Text, Markdown, JSON)
```

---

## 🧪 Executando os Testes

A suíte de testes unitários e de integração utiliza mocks para não depender de credenciais reais:

```bash
# Executando com unittest padrão do Python
python -m unittest discover -s tests -v

# Ou com pytest (se instalado)
pytest -v
```

---

## 🧩 Como Estender para Novos Recursos ou Provedores

### 1. Novo Recurso AWS (Ex: Elastic IP desanexado)
- Crie `AWSEIPCollector` herdando de `BaseResourceCollector`.
- Crie a regra `UnattachedEIPRule` herdando de `BaseInefficiencyRule`.
- Registre no `default_registry` em `providers/aws/__init__.py`.

### 2. Novo Recurso GCP (Ex: Persistent Disk inativo)
- Crie `GCPPersistentDiskCollector` herdando de `BaseResourceCollector`.
- Crie a regra `InactivePersistentDiskRule` herdando de `BaseInefficiencyRule`.
- Registre no `default_registry` em `providers/gcp/__init__.py`.

### 3. Novo Provedor Cloud (Ex: Azure)
- Crie o pacote `providers/azure/`.
- Implemente as interfaces `BaseResourceCollector`, `BaseMetricsProvider` e `BasePricingProvider`.
- Crie e registre as regras específicas do provedor.

---

## 📌 Versionamento e Changelog

Este projeto adere ao [Semantic Versioning (SemVer)](https://semver.org/lang/pt-BR/). Todas as alterações e notas de lançamento são documentadas no arquivo [CHANGELOG.md](CHANGELOG.md).

Para instalar uma versão específica:
```bash
pip install git+https://github.com/paulorosa/cloud-resource-inefficiency.git@v0.2.0
```

---

## 📄 Licença

Distribuído sob a licença MIT. Consulte [LICENSE](LICENSE) para mais informações.
