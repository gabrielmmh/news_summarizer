# Arquitetura do Sistema

Documentação técnica das decisões de arquitetura e design.

## Visão Geral

Sistema de pipeline automatizado para coleta, processamento e distribuição de notícias sumarizadas.

```
Portais → Crawlers → Validação → Storage → LLM → Email → Gestores
```

## Componentes Principais

### 1. Orquestração - Apache Airflow

**Função**: Coordenar e agendar todo o pipeline

**Por que Airflow?**
- Padrão da indústria (usado por Airbnb, Twitter, Spotify)
- DAGs como código (versionável no Git)
- Interface gráfica para monitoramento
- Retry automático e tratamento de erros
- Agendamento robusto com cron
- Paralelização nativa

**Alternativas consideradas**:
- Prefect: Menos maduro, comunidade menor
- Luigi: Menos features que Airflow
- Cron + scripts: Muito primitivo, sem retry logic

### 2. Banco de Dados - PostgreSQL

**Função**: Armazenar dados estruturados

**Esquema**:
```sql
news_articles:
- id, url, portal, title, content
- published_date, collected_at
- processed, html_s3_key

news_summaries:
- id, summary_date, summary_text
- news_count, theme, s3_key

email_logs:
- id, summary_id, recipient_email
- sent_at, status, error_message
```

**Por que PostgreSQL?**
- Dados relacionais bem definidos
- ACID compliance (consistência garantida)
- Queries complexas (filtros, joins, agregações)
- Integração nativa com Airflow
- Maduro e bem documentado

**Alternativas**:
- MongoDB: Não oferece vantagens para dados estruturados
- MySQL: Menos recursos que PostgreSQL

### 3. Armazenamento - MinIO

**Função**: Armazenar objetos não estruturados

**Estrutura**:
```
news-storage/
├── html/
│   ├── IstoÉDinheiro/
│   │   └── 20241012_123456_article.html
│   └── MoneyTimes/
│       └── 20241012_123457_article.html
└── summaries/
    └── 2024-10-12.txt
```

**Por que MinIO?**
- Compatível com S3 (migração fácil para cloud)
- Eficiente para arquivos grandes (HTML completo)
- Não sobrecarrega PostgreSQL
- Deploy fácil em Docker
- Baixo custo

**Alternativas**:
- AWS S3 direto: Mais caro para desenvolvimento
- Sistema de arquivos: Não escala bem

**Estratégia Híbrida**:
- PostgreSQL: Metadados, URLs, datas, relacionamentos
- MinIO: HTMLs brutos, resumos completos, logs

### 4. LLM - OpenAI GPT-4o-mini

**Função**: Gerar resumos executivos das notícias

**Por que GPT-4o-mini?**
- Melhor custo-benefício absoluto
- Input: $0.15/1M tokens (20x mais barato que GPT-4)
- Output: $0.60/1M tokens
- Qualidade excelente para sumarização
- API simples e estável
- Velocidade (2-5 segundos por resumo)

**Comparação de Modelos**:

| Modelo | Input | Output | Qualidade | Uso |
|--------|-------|--------|-----------|-----|
| GPT-4o-mini | $0.15/1M | $0.60/1M | ⭐⭐⭐⭐⭐ | Produção |
| GPT-4o | $2.50/1M | $10.00/1M | ⭐⭐⭐⭐⭐ | Se precisar do melhor |
| Claude Sonnet | $3.00/1M | $15.00/1M | ⭐⭐⭐⭐⭐ | Textos muito longos |

**Decisão**: GPT-4o-mini oferece ~95% da qualidade por 5-10% do custo.

### 5. Web Scraping - BeautifulSoup

**Função**: Extrair conteúdo HTML dos portais

**Por que BeautifulSoup?**
- Simples e eficiente para HTML estático
- 10-20x mais rápido que Selenium
- Menos recursos (sem browser necessário)
- Suficiente para portais escolhidos

**Quando usar Selenium?**
- Sites com JavaScript pesado (SPAs)
- Conteúdo carregado dinamicamente
- Autenticação complexa

**Situação atual**: IstoÉDinheiro e MoneyTimes não precisam de Selenium.

## Fluxo de Dados

```
1. Crawlers (Paralelo)
   ├─ IstoÉDinheiro: 15 artigos
   └─ MoneyTimes: 15 artigos
        ↓
2. Validação
   - Campos obrigatórios
   - Conteúdo mínimo (100 chars)
   - URLs válidas
   - Duplicatas
        ↓
3. Armazenamento
   ├─ PostgreSQL: metadados (id, url, title, date)
   └─ MinIO: HTML completo
        ↓
4. Busca e Preparação
   - Buscar artigos do dia
   - Truncar conteúdo longo (500 chars)
   - Limitar quantidade (20 artigos)
        ↓
5. Sumarização (OpenAI)
   - Prompt estruturado
   - Temperature: 0.7
   - Max tokens: 1500
   - Output: Markdown
        ↓
6. Email
   - Converter Markdown → HTML
   - Aplicar template Jinja2
   - Enviar via SMTP
        ↓
7. Logs
   - Registrar envio
   - Tokens usados
   - Status (sucesso/falha)
```

## Estrutura do DAG

```python
start
  ↓
crawling_group (parallel)
  ├─ crawl_istoe_dinheiro
  └─ crawl_moneytimes
  ↓
validate_articles
  ↓
store_articles
  ↓
generate_summary
  ↓
send_emails
  ↓
end

failure_alert ← (acionado em caso de erro)
```

**Recursos utilizados**:
- Paralelização (crawlers simultâneos)
- XCom (passagem de dados entre tasks)
- Trigger rules (failure_alert com `one_failed`)
- Retry logic (2 tentativas, 5min delay)

## Padrões de Design

### Factory Pattern

```python
BaseCrawler (abstrato)
  ├─ IstoeDinheiroCrawler
  └─ MoneyTimesCrawler
```

Facilita adição de novos portais sem modificar código existente.

### Template Method Pattern

```python
BaseCrawler.crawl_all():
    urls = self.crawl_homepage()      # Implementado por filho
    for url in urls:
        data = self.crawl_article(url) # Implementado por filho
```

### Repository Pattern

```python
NewsDatabase:
    insert_article()
    get_recent_articles()
    mark_processed()
```

Abstrai acesso ao banco de dados.

## Decisões Arquiteturais

### Storage Híbrido (PostgreSQL + MinIO)

**Decisão**: Usar dois sistemas de armazenamento

**Justificativa**:
- PostgreSQL: Ótimo para queries, relacionamentos, índices
- MinIO: Ótimo para blobs, arquivos grandes
- Performance otimizada para cada tipo de dado
- Custos reduzidos (object storage é mais barato)
- Escala independentemente

### Monolito Modular vs Microservices

**Decisão**: Monolito modular

**Justificativa**:
- Escopo pequeno (30 notícias/dia)
- Deploy simples (um docker-compose)
- Menos complexidade operacional
- Mais fácil de debugar
- Preparado para modularizar se crescer

### Processamento Síncrono

**Decisão**: Pipeline síncrono com paralelização

**Justificativa**:
- Airflow já gerencia paralelização
- Tasks independentes rodam em paralelo
- Execução sequencial onde há dependência
- Retry automático incluído
- Mais simples que async/await

## Performance

### Métricas Esperadas

| Fase | Tempo Médio |
|------|-------------|
| Crawling (paralelo) | ~2 min |
| Validação | ~5 seg |
| Storage | ~30 seg |
| LLM (OpenAI) | ~30 seg |
| Email | ~30 seg |
| **Total** | **~4-5 min** |

### Otimizações Implementadas

- Crawlers rodam em paralelo
- Rate limiting (2s delay entre requests)
- Truncar conteúdo longo (500 chars)
- Limitar artigos processados (20)
- Max tokens LLM (1500)
- Connection pooling (PostgreSQL)

### Otimizações Futuras

- Cache Redis (evitar reprocessar)
- Batch processing
- CDN para HTMLs estáticos
- Processamento assíncrono

## Escalabilidade

### Vertical (Curto Prazo)

- Aumentar CPU/RAM dos containers
- PostgreSQL: read replicas
- MinIO: distributed mode
- Airflow: mais workers

### Horizontal (Longo Prazo)

- Kubernetes deployment
- Celery workers distribuídos
- S3 (substituir MinIO)
- Redis cluster
- Load balancer

### Limites Atuais

- Artigos/dia: 30
- Tokens/dia: ~20k
- Emails/dia: Ilimitado
- Storage: ~10GB/ano

## Segurança

### Implementado

✅ Variáveis de ambiente (não hardcoded)
✅ `.gitignore` para `.env`
✅ Rate limiting (respeita servidores)
✅ User-Agent customizado
✅ TLS para SMTP

### Planejado

- Secrets management (HashiCorp Vault)
- API key rotation automática
- Network policies
- Encryption at rest

## Custos

### Desenvolvimento

| Item | Custo/Mês |
|------|-----------|
| Docker local | R$0 |
| OpenAI | R$3-6 |
| Gmail SMTP | R$0 |
| **Total** | **R$3-6** |

### Produção (AWS)

| Item | Custo/Mês |
|------|-----------|
| EC2 t3.medium | R$150 |
| RDS PostgreSQL | R$100 |
| S3 | R$10 |
| OpenAI API | R$30 |
| AWS SES | R$5 |
| **Total** | **R$295** |

### ROI

- Tempo economizado: ~2h/dia lendo notícias
- Custo humano: ~R$50/h × 2h × 22 dias = R$2.200/mês
- Custo do sistema: R$295/mês
- **Economia líquida**: R$1.905/mês
- **ROI**: 645%

## Estatísticas do Projeto

| Métrica | Valor |
|---------|-------|
| Arquivos totais | 31 |
| Linhas Python | ~2.000 |
| Arquivos documentação | 3 |
| Portais suportados | 2 |
| Tabelas database | 3 |
| Testes | Sim |
| Docker | Sim |
| CI/CD | Preparado |

## Testes

### Unitários

```python
tests/test_crawlers.py:
- test_normalize_url()
- test_fetch_html_success()
- test_fetch_html_failure()
```

### Integração (Planejado)

- Pipeline completo end-to-end
- Mock OpenAI responses
- Validar email enviado

### Manuais

```bash
# Testar crawler
python -m src.crawlers.istoe_crawler

# Testar LLM
python -m src.llm.summarizer
```

## Monitoramento

### Métricas Importantes

1. **Pipeline health**: Taxa de sucesso, tempo de execução
2. **Data quality**: % validados, duplicatas
3. **Custos**: Tokens OpenAI, storage usado
4. **Delivery**: Emails enviados, bounces

### Ferramentas

- Airflow UI: Logs e status das tasks
- PostgreSQL: Queries analíticas
- MinIO Console: Uso de storage
- OpenAI Dashboard: Consumo de tokens

### Alertas

- Pipeline failure → Email para admin
- Cost threshold → Notificação
- Storage full → Alerta

## Melhorias Futuras

### Curto Prazo

- [ ] Redis cache (deduplicação)
- [ ] Mais portais de notícias
- [ ] Testes de integração
- [ ] CI/CD pipeline

### Médio Prazo

- [ ] Dashboard Grafana
- [ ] Análise de sentimento
- [ ] Preferências por usuário
- [ ] API REST

### Longo Prazo

- [ ] App mobile
- [ ] Processamento real-time
- [ ] Suporte multi-idioma
- [ ] ML para priorização

## Referências

- Airflow: https://airflow.apache.org/docs
- OpenAI: https://platform.openai.com/docs
- MinIO: https://min.io/docs
- PostgreSQL: https://postgresql.org/docs

---

*Para configuração, veja [SETUP.md](SETUP.md)*
