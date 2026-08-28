# ADR-0004: Async-First Metrics Collection Strategy

## Status
Accepted

## Context

Coleta de métricas é uma operação **I/O-bound** de alta latência:
- Chamadas para CloudWatch (AWS) podem levar 500ms-2s por métrica
- Chamadas para Cloud Monitoring (GCP) podem levar 1-3s
- Chamadas para Azure Monitor podem levar 800ms-2s
- Em um scan com 50 recursos e 3 métricas cada = 150 chamadas = potencial **5-15 minutos de tempo total**

Processamento **sequencial** é ineficiente:
```python
# Sequencial (lento)
for resource in resources:  # 50 recursos
    metrics = metrics_provider.get_metrics(resource)  # 1-3s cada
    # Total: 50-150 segundos
```

Processamento **assíncrono** pode paralelizar:
```python
# Assíncrono (rápido)
tasks = [metrics_provider.get_metrics_async(r) for r in resources]
results = await asyncio.gather(*tasks)  # Executam em paralelo
# Total: 3-5 segundos (limitado pela chamada mais lenta, não pela soma)
```

Entretanto, o projeto está em **fase alpha** com:
- Base de código pequena (< 5000 linhas)
- Equipe pequena (iniciativa de 1-2 pessoas)
- Prioridade inicial é **corretude, não performance**
- Escala esperada: 100-1000 recursos por scan

## Decision

Adotar estratégia **"Async-Ready, Sequential Now"**:

1. **Hoje (v0.x)**: Manter processamento **sequencial** nos `BaseMetricsProvider`
2. **Amanhã (v1.0+)**: Design preparado para easy refactor para `async/await`

Código preparado para async:
```python
# core/interfaces.py - Preparação para async
class BaseMetricsProvider(ABC):
    @abstractmethod
    def get_metrics(self, resource: CloudResource, ...) -> MetricSummary:
        """Versão síncrona, pode ser wrappada em async"""
        pass
    
    # Futuro: async def get_metrics_async(...)
```

Exemplo de como será fácil fazer o refactor:
```python
# providers/aws/metrics/cloudwatch.py
class AWSCloudWatchMetricsProvider(BaseMetricsProvider):
    def get_metrics(self, resource: CloudResource, ...) -> MetricSummary:
        # Implementação atual: síncrona
        client = self.client_factory.get_client('cloudwatch', resource.region)
        return self._parse_metrics(client.get_metric_statistics(...))
    
    # Futuro:
    async def get_metrics_async(self, resource: CloudResource, ...) -> MetricSummary:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_metrics, resource)
```

E no scanner:
```python
# engine/scanner.py
async def scan_async(self, ...):
    """Versão assíncrona do scan"""
    tasks = [
        metrics_provider.get_metrics_async(resource)
        for resource in resources
    ]
    metrics = await asyncio.gather(*tasks)
    # ... resto da lógica
```

## Rationale

1. **Pragmatismo**: Phase-gated approach. Resolve problema quando ele existir (premature optimization is evil)
2. **Não Breaking**: Design síncrono atual não impede refactor posterior
3. **Simplicidade**: Código síncrono é mais fácil debugar, entender, testar
4. **Escalabilidade**: Fácil adicionar async version quando performance virar prioridade
5. **Compatibilidade**: Código consumidor funciona com ou sem async
6. **Aprendizado**: Time ganha experiência com padrão antes de escalar

## Consequences

### Positive
- ✅ Código mais simples, mais fácil debugar problemas operacionais
- ✅ Sem complexidade adicional de event loops, futures, locks assincronos
- ✅ Design preparado para refactor sem breaking changes
- ✅ CI/CD rápido (sem need para test async behavior now)
- ✅ Performance aceitável para escala atual (< 1000 recursos)

### Negative
- ❌ Performance subótima em alta escala (1M+ recursos)
- ❌ Bloqueios de I/O podem congelar thread principal
- ❌ Sem paralelização = sem aproveitar multi-core
- ❌ Scans longos podem timeout em CI/CD com timeout restrictivo

## Alternatives Considered

### 1. Full Async/Await Agora
```python
async def get_metrics_async(self, resource: CloudResource, ...) -> MetricSummary:
    # Implementação completa com asyncio
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return parse(await resp.json())
```
**Rejeitado**: Over-engineered para estágio atual. Adiciona complexidade:
- Todos os consumers precisam ser async
- Testes precisam de async fixtures/mocks
- Documentação e learning curve aumenta
- Sem benefício imediato (poucos recursos em scan)

### 2. ThreadPoolExecutor (Paralelização Síncrona)
```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=5) as executor:
    metrics = list(executor.map(get_metrics, resources))
```
**Rejeitado Parcialmente**: Bom trade-off, mas:
- Introduz threads (sincronização complexa)
- Boto3, Google SDK, Azure SDK não são totalmente thread-safe sem cuidados
- Pode provocar rate limiting da API se não coordenar bem
- Mais complexo para debugar (stack traces confusos)

### 3. ProcessPoolExecutor (Paralelização com Multiprocessing)
```python
from concurrent.futures import ProcessPoolExecutor

with ProcessPoolExecutor(max_workers=4) as executor:
    metrics = list(executor.map(get_metrics, resources))
```
**Rejeitado**: Complexo demais:
- Pickling de objetos é overhead
- Clientes cloud não são serializáveis
- Cada processo precisa de suas credenciais
- Overkill para timing esperado

## Related Decisions

- **ADR-0005**: Caching é complementar a async (reduz I/O ainda mais)
- **ADR-0006**: Resilience com retry complementa async (retries de timeout)

## Implementation References

### Current Files (Síncrono)
- `src/cloud_resource_inefficiency/providers/aws/metrics/cloudwatch.py`
  - `AWSCloudWatchMetricsProvider.get_metrics()` - síncrono
- `src/cloud_resource_inefficiency/providers/gcp/metrics/monitoring.py`
  - `GCPMonitoringMetricsProvider.get_metrics()` - síncrono
- `src/cloud_resource_inefficiency/engine/scanner.py`
  - Loop sequencial em `scan()`

### Future Refactor (Async)
```python
# Será algo assim em v1.0+
class AWSCloudWatchMetricsProvider(BaseMetricsProvider):
    async def get_metrics_async(self, resource: CloudResource, ...) -> MetricSummary:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,  # Use default ThreadPoolExecutor
            self.get_metrics,
            resource
        )

# No scanner:
async def scan_async(self, ...) -> ScanResult:
    # ... coleta de recursos
    tasks = [
        metrics_provider.get_metrics_async(resource, ...)
        for resource in resources
    ]
    metrics_results = await asyncio.gather(*tasks, return_exceptions=True)
    # ... resto da lógica
```

## Notes

- **Async Runtime**: Quando implementar async, considerar usar `asyncio` (stdlib) ao invés de bibliotecas terceiras (mais simples)
- **Rate Limiting**: Cloud providers têm limits (ex: CloudWatch API calls/segundo). Com async, esses limites ficarão mais evidentes - será necessário implementar backoff inteligente
- **Error Handling**: Async torna mais fácil coletar erros de múltiplas requisições concorrentes e reportar todos, ao invés de falhar na primeira
- **Testing**: Async torna possível testar timeouts e retry logic mais realista
