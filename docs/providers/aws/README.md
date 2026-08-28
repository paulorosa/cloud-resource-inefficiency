# AWS Cloud Provider Documentation

Documentação completa para detecção de ineficiências em recursos AWS usando cloud-resource-inefficiency.

## 📦 Oportunidades de Custo Implementadas

### Inactive and Detached EBS Volume (AWS-EBS-001)

**Descrição**: Detecta volumes EBS não anexados a instâncias EC2 que não estão sendo utilizados.

#### Critérios de Detecção
- Estado vailable (sem instâncias EC2 anexadas)
- Análise de métricas do CloudWatch em janela configurável (padrão: 14 dias)
  - VolumeReadOps
  - VolumeWriteOps
  - VolumeReadBytes
  - VolumeWriteBytes
- Volume considerado inativo se I/O = 0 durante a janela

#### Precificação
- **Fonte Primária**: AWS Pricing API (get_products em us-east-1 com cache em memória)
- **Fallback**: Tabela de tarifas padrão com suporte a volumes:
  - gp2, gp3, io1, io2
  - st1 (Throughput Optimized)
  - sc1 (Cold HDD)
  - standard
- Inclui custo de IOPS provisionados (io1/io2) e throughput (st1/sc1)

#### Valor de Oportunidade
Economia mensal estimada (/mês) baseada no tipo e tamanho do volume.

#### Análise de Risco
- **LOW**: Sem snapshots recentes, sem tags de retenção
- **MEDIUM**: Tem snapshots ou tags parciais
- **HIGH**: Snapshots recentes, múltiplas tags de retenção, backup crítico

Tags analisadas: DoNotDelete, Backup, Retain, Critical

#### Nível de Confiança
- **HIGH**: Volume claramente inativo (0 I/O por 14+ dias)
- **MEDIUM**: Métrica incompleta ou período de observação reduzido
- **LOW**: Dados limitados ou inconsistentes

#### Remediação Recomendada
`ash
# Criar snapshot de backup (segurança)
aws ec2 create-snapshot --volume-id vol-xxxxx --description "Backup antes de deletar"

# Aguardar conclusão do snapshot
aws ec2 describe-snapshots --snapshot-ids snap-xxxxx --query 'Snapshots[0].State'

# Deletar volume
aws ec2 delete-volume --volume-id vol-xxxxx --region us-east-1
`

## 💡 Exemplo de Uso

`python
from cloud_resource_inefficiency import (
    CloudProvider,
    InefficiencyScanner,
    ResourceType,
    ScanResultFormatter,
)

# Scan de volumes EBS inativos em todas as regiões
scanner = InefficiencyScanner(
    providers=[CloudProvider.AWS],
    regions=["us-east-1", "sa-east-1", "eu-west-1"],  # ou "all"
)

result = scanner.scan(
    resource_types=[ResourceType.AWS_EBS_VOLUME],
    lookback_days=14,
)

# Saída formatada
print(ScanResultFormatter.to_text_summary(result))
print(ScanResultFormatter.to_markdown(result))

# JSON para pipelines CI/CD
import json
json_data = json.loads(ScanResultFormatter.to_json(result))
print(json.dumps(json_data, indent=2))
`

## 🔍 Saída de Exemplo

`	ext
======================================================================
               CLOUD FINANCIAL INEFFICIENCY SCAN REPORT
======================================================================
Total Scanned Resources: 25
Opportunities Found:     3
Total Monthly Savings:   102.40 USD
Annual Projected Saving: 1,228.80 USD
----------------------------------------------------------------------
Rule ID    | Resource ID            | Region       | Savings/Mo   | Risk    
----------------------------------------------------------------------
AWS-EBS-001| vol-0123456789abcdef0  | us-east-1    | $    48.00   | LOW     
AWS-EBS-001| vol-0987654321fedcba1  | sa-east-1    | $    27.20   | MEDIUM  
AWS-EBS-001| vol-1122334455667788aa | eu-west-1    | $    27.20   | HIGH    
======================================================================
`

## 🧪 Testes

Testes para AWS estão em 	tests/:
- 	test_aws_collectors.py — Coleta de volumes EBS
- 	test_aws_metrics.py — Métricas CloudWatch
- 	test_aws_pricing.py — Precificação
- 	test_aws_rules.py — Lógica de detecção
- 	test_core_models.py — Modelos genéricos

Execute com:
`ash
pytest tests/ -k aws -v
`

## 📚 Relacionados

- [GCP Documentation](../gcp/README.md)
- [Azure Documentation](../azure/README.md)
- [Architecture Decision Records](../../adr/README.md)

## ℹ️ Mais Informações

- [AWS Pricing API Documentation](https://docs.aws.amazon.com/aws-cost-management/latest/userguide/ce-api.html)
- [CloudWatch Metrics for EBS](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using_cloudwatch_ebs.html)
- [EC2 User Guide](https://docs.aws.amazon.com/ec2/)