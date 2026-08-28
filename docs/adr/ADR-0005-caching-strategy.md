# ADR-0005: Caching Strategy for Pricing and Metrics

## Status
Accepted

## Context

Múltiplas chamadas repetidas ocorrem durante um scan:
- **Pricing**: Mesmo tipo de recurso em múltiplas regiões usa mesma tarifa
- **Metrics**: Múltiplos recursos podem consultar cloudwatch para mesma métrica em timeframe sobreposto

Exemplo:
```
Scan com 100 volumes EBS em us-east-1:
- 100 × get_pricing(gp2) → 100 chamadas para AWS Pricing API (mesma resposta!)
- 100 × get_metrics(resource) → 100 chamadas para CloudWatch (pode ter sobreposição)
```

Sem cache:
- Rate limiting da API cloud (throttling, rejeições)
- Latência aumentada: 100 chamadas × 0.5s = 50 segundos desnecessários
- Custo potencial de API calls (AWS Pricing API pode ter custos)

Com cache:
- 1ª chamada: Hit API, armazena resultado
- 2-100ª chamadas: Retorna do cache instantaneamente
- Economia: ~49.5 segundos

Entretanto:
- Cache de métricas tem validade limitada (dados desatualizam)
- Pricing muda periodicamente (não cache infinito)
- TTL complexo pode introduzir bugs

## Decision

Implementar **in-memory cache com threading.Lock**, sem TTL explícito:

### Para Pricing
```python
# providers/aws/pricing/aws_pricing.py
class AWSPricingProvider(BasePricingProvider):
    def __init__(self):
        self._cache: Dict[str, PricingDetails] = {}
        self._lock = threading.Lock()
    
    def get_pricing_details(self, resource: CloudResource, ...) -> PricingDetails:
        cache_key = f"{resource.resource_type.value}:{resource.region}:{volume_type}"
        
        with self._lock:
            if cache_key in self._cache:
                logger.debug(f"Pricing cache hit: {cache_key}")
                return self._cache[cache_key]
        
        # Cache miss: Chamar AWS Pricing API
        pricing = self._fetch_from_api(...)
        
        with self._lock:
            self._cache[cache_key] = pricing
        
        return pricing
```

### Para Métricas
```python
# Caching é por-resource + por-metric-type + por-timeframe
# Exemplo: CloudWatch cache hit se pedirmos mesma métrica para recurso em mesmo período

class AWSCloudWatchMetricsProvider(BaseMetricsProvider):
    def __init__(self):
        self._metrics_cache: Dict[str, MetricSummary] = {}
        self._lock = threading.Lock()
    
    def get_metrics(self, resource: CloudResource, lookback_days: int) -> MetricSummary:
        cache_key = f"{resource.resource_id}:{lookback_days}"
        
        with self._lock:
            if cache_key in self._metrics_cache:
                return self._metrics_cache[cache_key]
        
        # Cache miss: Consultar CloudWatch
        metrics = self._fetch_from_cloudwatch(...)
        
        with self._lock:
            self._metrics_cache[cache_key] = metrics
        
        return metrics
```

### Overhead Mínimo
```python
# Caches são implícitos (não expostos à API)
pricing = pricing_provider.get_pricing_details(resource)  # Automaticamente cacheado

metrics = metrics_provider.get_metrics(resource, lookback_days=14)  # Automaticamente cacheado
```

## Rationale

1. **Simplicidade**: In-memory, sem dependências de Redis/memcached
2. **Performance**: O(1) lookup em dicionários Python
3. **Validade**: Cache vive apenas durante scan (não persiste entre execuções)
4. **Segurança**: `threading.Lock` garante thread-safety sem deadlock
5. **Sem TTL**: Scan individual não se beneficia de TTL complexo. Dados estão garantidos frescos para janela temporal do scan
6. **Possível Invalidação**: Caller pode explicitamente limpar cache se necessário

## Consequences

### Positive
- ✅ Dramaticamente reduz chamadas à API cloud (50-100x em alguns cenários)
- ✅ Tempo de scan reduzido significativamente
- ✅ Sem dependências externas (Redis, memcached)
- ✅ Thread-safe: múltiplos workers podem compartilhar provider
- ✅ Fácil debugar cache hits (logging em DEBUG level)
- ✅ Implícito para consumidores (transparent)

### Negative
- ❌ Dados stale se cache persiste entre scans (precisa ser resetado)
- ❌ Memory overhead: Preços de 1000s de recursos × regiões podem consumir MB
- ❌ Sem controle fino do caller sobre cache (cache sempre ativo)
- ❌ Possível memory leak se provider viver muito tempo (cache nunca limpo)
- ❌ Debugging complexo: "Por que este resultado é diferente?"

## Alternatives Considered

### 1. Redis Cache
```python
import redis
cache = redis.Redis(host='localhost', port=6379)
pricing = cache.get(cache_key)  # if None, fetch from API
```
**Rejeitado**: 
- Requer Redis rodando (operacional complexity)
- Overkill para escala atual
- Latência de rede adicional (Redis não está na mesma máquina)
- Custo operacional

### 2. TTL-Based In-Memory Cache
```python
from cachetools import TTLCache
cache = TTLCache(maxsize=10000, ttl=3600)  # 1 hora
cache[key] = value
```
**Rejeitado Parcialmente**: TTL não é necessário para um scan atomic
- Se scan leva 5 minutos e TTL é 1 hora, TTL nunca expira durante scan
- Entre scans, cache sendo descartado de qualquer forma
- Complexidade adicional sem benefício

### 3. Sem Cache
```python
# Sem cache, chamar API sempre
pricing = aws_pricing_api.get_products(...)  # Sempre fresh
```
**Rejeitado**: Performance ruim, rate limiting, latência excessiva

### 4. LRU Cache (Least Recently Used)
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_pricing_details(self, resource_type: str, region: str) -> PricingDetails:
    return self._fetch_from_api(...)
```
**Rejeitado**: 
- `@functools.lru_cache` não é thread-safe por padrão
- Requer sincronização manual
- Menos control sobre invalidação

## Related Decisions

- **ADR-0004**: Async-First complementa cache (ambos reduzem I/O efetivo)
- **ADR-0006**: Resilience works together com cache (retry falhos não são cacheados)

## Implementation References

### Key Files
- `src/cloud_resource_inefficiency/providers/aws/pricing/aws_pricing.py`
  - Cache para resultados de AWS Pricing API
  - `_cache: Dict[str, PricingDetails]`
  - `_lock: threading.Lock`
- `src/cloud_resource_inefficiency/providers/aws/metrics/cloudwatch.py`
  - Cache para resultados de CloudWatch
- `src/cloud_resource_inefficiency/providers/gcp/pricing/gcp_pricing.py`
  - Cache para tarifas GCS
- `src/cloud_resource_inefficiency/providers/azure/pricing/azure_pricing.py`
  - Cache para tarifas Azure

### Cache Key Strategy
```python
# Pricing: provider + resource_type + region + (opcional) sku
pricing_cache_key = f"pricing:{provider}:{resource_type}:{region}:{volume_type}"

# Metrics: resource_id + metric_name + lookback_days
metrics_cache_key = f"metrics:{resource_id}:{metric_name}:{lookback_days}"
```

### Usage Example
```python
# Pricing cache (automático)
pricing1 = aws_pricing_provider.get_pricing_details(vol1)  # Hit API, cache
pricing2 = aws_pricing_provider.get_pricing_details(vol2)  # Cache hit (mesma region/type)

# Metrics cache (automático)
metrics1 = cloudwatch_provider.get_metrics(vol1, lookback_days=14)  # Hit API, cache
metrics2 = cloudwatch_provider.get_metrics(vol1, lookback_days=14)  # Cache hit (mesmo recurso/periodo)
```

## Notes

- **Cache Invalidation**: Phil Karlton disse "There are only two hard things in Computer Science: cache invalidation and naming things." Este design evita invalidação dinâmica - cache vive só durante scan
- **Memory Growth**: Se aplicação executar 100s de scans, considerar implementar LRU eviction ou explicit cache cleanup
- **Metrics Accuracy**: Cache de métricas assume que dados não mudam durante scan. Se scan leva 30 minutos, métricas podem estar levemente desatualizado - tradeoff aceitável
- **Distributed Scenarios**: Se houver múltiplos workers/threads, lock garante consistência. Mas se houver múltiplos *processos*, cache não é compartilhado - cada processo tem seu próprio cache
