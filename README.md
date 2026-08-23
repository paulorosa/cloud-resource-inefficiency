# Cloud Resource Inefficiency (`cloud-resource-inefficiency`)

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Uma biblioteca Python moderna, modular e extensível para **identificação de oportunidades financeiras e ineficiências de custo em recursos de nuvem multi-provedor** (AWS, Azure, GCP).

Desenvolvida seguindo os princípios **SOLID**, padrões de projeto Orientados a Objetos (**Strategy**, **Registry**, **DTOs** e injeção de dependências) e tipagem estrita com `dataclasses`.

---

## 🎯 Oportunidades Implementadas

### 1. Inactive and Detached EBS Volume ([PointFive CER-0066](https://hub.pointfive.co/inefficiencies/inactive-and-detached-ebs-volume))
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

---

## 🚀 Instalação

```bash
git clone https://github.com/paulorosa/cloud-resource-inefficiency.git
cd cloud-resource-inefficiency
pip install -e .
```

---

## 💡 Guia de Uso Rápido

### Exemplo em Python:

```python
from cloud_resource_inefficiency import (
    CloudProvider,
    InefficiencyScanner,
    ResourceType,
    ScanResultFormatter,
)

# 1. Instanciar o scanner
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

### Formatos de Exportação:
- `ScanResultFormatter.to_text_summary(result)`: Tabela formatada para terminal.
- `ScanResultFormatter.to_markdown(result)`: Relatório completo em Markdown.
- `ScanResultFormatter.to_json(result)`: Payload JSON estruturado para integrações ou pipelines CI/CD.
- `ScanResultFormatter.to_dict(result)`: Dicionário Python serializável.

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
│   └── aws/
│       ├── client_factory.py  # Gerenciador de clientes boto3
│       ├── collectors/        # Coleta de inventário (AWSEBSCollector)
│       ├── metrics/           # CloudWatch (AWSCloudWatchMetricsProvider)
│       ├── pricing/           # AWS Pricing API + Fallback Rates (AWSPricingProvider)
│       └── rules/             # Regras de detecção (InactiveDetachedEBSVolumeRule)
├── engine/
│   └── scanner.py             # Motor InefficiencyScanner
└── formatters/
    └── output.py              # Formatadores de saída (Text, Markdown, JSON)
```

---

## 🧪 Executando os Testes

A suíte de testes unitários e de integração utiliza mocks para não depender de credenciais reais da AWS:

```bash
# Executando com unittest padrão do Python
python -m unittest discover -s tests -v

# Ou com pytest (se instalado)
pytest -v
```

---

## 🧩 Como Estender para Novos Recursos ou Provedores

1. **Novo Recurso AWS (Ex: Elastic IP desanexado)**:
   - Crie `AWSEIPCollector` herdando de `BaseResourceCollector`.
   - Crie a regra `UnattachedEIPRule` herdando de `BaseInefficiencyRule`.
   - Registre no `default_registry`.
2. **Novo Provedor Cloud (Ex: Azure ou GCP)**:
   - Crie o pacote `providers/azure/` ou `providers/gcp/`.
   - Implemente as interfaces `BaseResourceCollector`, `BaseMetricsProvider` e `BasePricingProvider`.
   - Crie e registre as regras específicas do provedor.

---

## 📄 Licença

Distribuído sob a licença MIT. Consulte [LICENSE](LICENSE) para mais informações.
