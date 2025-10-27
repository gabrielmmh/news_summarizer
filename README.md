# News Summarizer - Pipeline Automatizado de Notícias

Sistema que coleta notícias de múltiplos portais, gera resumos executivos com IA e distribui por email diariamente.

---

## Stack Tecnológico

- **Airflow** 2.10 - Orquestração de pipeline
- **PostgreSQL** 15 - Banco de dados estruturado
- **MinIO** - Object storage (S3-compatible)
- **OpenAI** GPT-4o-mini - Sumarização com IA
- **BeautifulSoup** 4.12 - Web scraping
- **Flask** 3.0 - Gerenciamento de preferências

---

## Pré-requisitos

Antes de começar, você precisa ter:

1. **Docker** e **Docker Compose** instalados
2. **Conta OpenAI** com $5 de crédito (dura meses)
3. **Gmail** com verificação em duas etapas ativada

---

## Configuração Rápida

### 1. Configurar OpenAI

**a) Criar conta e adicionar créditos:**
```
1. Acesse: https://platform.openai.com/signup
2. Faça login/cadastro
3. Vá em: https://platform.openai.com/account/billing
4. Adicione $5 USD no cartão
```

**b) Gerar API Key:**
```
1. Acesse: https://platform.openai.com/api-keys
2. Clique em "Create new secret key"
3. Nome: "news-summarizer-aps01"
4. COPIE a chave (começa com sk-proj-)
```

### 2. Configurar Gmail SMTP

**a) Ativar verificação em 2 etapas:**
```
1. Acesse: https://myaccount.google.com/security
2. Ative "Verificação em duas etapas"
```

**b) Gerar senha de aplicativo:**
```
1. Acesse: https://myaccount.google.com/apppasswords
2. Nome: "APS News Summarizer"
3. Clique em "Gerar"
4. COPIE a senha de 16 caracteres
```

### 3. Criar arquivo .env

```bash
cd aps01
cp .env.example .env
nano .env
```

**Configure estas variáveis OBRIGATÓRIAS:**
```env
# OpenAI (cole sua chave aqui)
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxx

# Gmail SMTP (cole seu email e senha de app)
SMTP_USER=seu-email@gmail.com
SMTP_PASSWORD=abcd efgh ijkl mnop

# Destinatários (pode ser seu próprio email para testar)
RECIPIENT_EMAILS=seu-email@gmail.com
```

**Outras variáveis já vêm configuradas, mas você pode ajustar:**
```env
NEWS_THEME=economia                    # Tema das notícias
OPENAI_MODEL=gpt-4o-mini              # Modelo da OpenAI
SMTP_HOST=smtp.gmail.com              # Servidor SMTP
SMTP_PORT=587                         # Porta SMTP
```

### 4. Iniciar o sistema

```bash
docker-compose up -d
```

Aguarde 2 minutos para os containers iniciarem.

### 5. Executar primeira vez

**a) Acessar Airflow:**
```
URL: http://localhost:8080
Usuário: airflow
Senha: airflow
```

**b) Ativar e executar DAG:**
```
1. Na lista de DAGs, localize "news_summarizer_daily"
2. Toggle do lado esquerdo para ativar (ON)
3. Clique no nome do DAG
4. Botão "Trigger DAG" (play ▶️) no canto superior direito
5. Aguarde 2 a 3 minutos
```

**c) Verificar execução:**
```
- Status das tasks ficará verde quando concluir
- Verifique seu email (pode cair em spam na primeira vez)
```

✅ **Pronto!** Você receberá um resumo de notícias no email.

---

## Estrutura do Projeto

```
aps01/
├── dags/
│   └── news_summarizer_dag.py       # Pipeline principal (7 tasks)
│
├── src/
│   ├── crawlers/                    # Web scraping
│   │   ├── base_crawler.py          # Classe base abstrata
│   │   ├── istoe_crawler.py         # Crawler IstoÉDinheiro
│   │   └── moneytimes_crawler.py    # Crawler MoneyTimes
│   │
│   ├── llm/
│   │   └── summarizer.py            # Integração OpenAI GPT-4o-mini
│   │
│   ├── email/
│   │   ├── sender.py                # Envio SMTP com templates
│   │   └── templates/
│   │       └── news_digest.html     # Template HTML responsivo
│   │
│   ├── utils/
│   │   ├── database.py              # Interface PostgreSQL
│   │   └── storage.py               # Interface MinIO (S3)
│   │
│   └── web/
│       └── app.py                   # Flask app (preferências)
│
├── tests/
│   └── test_crawlers.py             # Testes unitários
│
├── docker-compose.yml               # Orquestração de containers
├── init-db.sql                      # Schema do banco
├── requirements.txt                 # Dependências Python
└── README.md                        
```

---

## Como Funciona

### Pipeline Completo (7 etapas)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. CRAWLING (paralelo)                                      │
│    ├─ IstoÉDinheiro → 15 artigos                           │
│    └─ MoneyTimes     → 15 artigos                           │
│                                                              │
│ 2. VALIDAÇÃO                                                │
│    └─ Verifica campos obrigatórios, conteúdo mínimo         │
│                                                              │
│ 3. ARMAZENAMENTO                                            │
│    ├─ PostgreSQL  → Metadados (título, data, portal)        │
│    └─ MinIO       → HTML completo                           │
│                                                              │
│ 4. SUMARIZAÇÃO                                              │
│    └─ OpenAI GPT-4o-mini → Resumo executivo                 │
│                                                              │
│ 5. ENVIO DE EMAILS                                          │
│    └─ SMTP → Email HTML com resumo                          │
│                                                              │
│ 6. LOGGING                                                  │
│    └─ Registra envios no banco                              │
│                                                              │
│ 7. ALERTA DE FALHA (se necessário)                          │
│    └─ Notifica erros por email                              │
└─────────────────────────────────────────────────────────────┘
```

### Agendamento

- **Frequência:** 2x por dia (7h e 18h)
- **Cron:** `0 7,18 * * *`
- **Execução manual:** Trigger DAG no Airflow UI

### Filtragem de Destinatários

Os emails são filtrados por:
1. **Lista do .env:** Apenas emails em `RECIPIENT_EMAILS` podem receber
2. **Preferências do usuário:**
   - Status da assinatura (ativo/cancelado)
   - Horário preferido (7h ou 18h)

---

## Funcionalidades

### ✅ Crawling Automático
- 2 portais de economia (IstoÉDinheiro + MoneyTimes)
- Até 30 artigos por execução
- Extrai: título, conteúdo, data de publicação

### ✅ Armazenamento Híbrido
- **PostgreSQL:** Metadados estruturados
- **MinIO:** HTML completo dos artigos
- Evita duplicatas (constraint por URL)

### ✅ Sumarização com IA
- Modelo: GPT-4o-mini
- Resumo executivo em português
- Título criativo gerado automaticamente
- Custo: ~R$0.01-0.03 por execução

### ✅ Email Personalizado
- Template HTML profissional e responsivo
- Título dinâmico baseado no conteúdo
- Links funcionais de preferências e cancelamento
- Envio individual com tokens únicos

### ✅ Gerenciamento de Preferências
- Página web para configurar preferências
- Escolher horário de recebimento (7h ou 18h)
- Cancelar/reativar assinatura
- Acesso via link no email (token SHA-256)

---

## Acessando o Sistema

| Serviço | URL | Credenciais |
|---------|-----|-------------|
| **Airflow** | http://localhost:8080 | airflow / airflow |
| **MinIO** | http://localhost:9001 | minioadmin / minioadmin |
| **Preferências** | http://localhost:5000 | Via link no email |
| **PostgreSQL** | localhost:5432 | airflow / airflow |

---

## Comandos Úteis

```bash
# Iniciar todos os containers
docker-compose up -d

# Ver logs em tempo real
docker-compose logs -f

# Ver logs de um serviço específico
docker-compose logs -f airflow-scheduler

# Parar todos os containers
docker-compose down

# Parar e remover TUDO (dados inclusos)
docker-compose down -v

# Reiniciar um serviço específico
docker-compose restart airflow-scheduler

# Acessar banco de dados
docker exec -it aps01-postgres-1 psql -U airflow -d news_db

# Ver uso de tokens OpenAI
docker-compose logs | grep "Tokens used"

# Executar testes
pytest tests/
```

---

## Troubleshooting

### OpenAI: "Invalid API Key"
**Problema:** Chave incorreta ou expirada
**Solução:**
```bash
# Verifique se a chave está correta no .env
cat .env | grep OPENAI_API_KEY

# Deve começar com: sk-proj-
# Se não funcionar, gere nova chave em:
# https://platform.openai.com/api-keys
```

### OpenAI: "You exceeded your quota"
**Problema:** Sem créditos na conta
**Solução:**
```
1. Adicione créditos: https://platform.openai.com/billing
2. Mínimo $5 USD
3. Aguarde 1-2 minutos e tente novamente
```

### Gmail: "Authentication failed"
**Problema:** Senha de aplicativo incorreta
**Solução:**
```
1. Verifique se a verificação em 2 etapas está ATIVA
2. Gere nova senha de app em:
   https://myaccount.google.com/apppasswords
3. Use a senha de 16 caracteres (não a senha normal do Gmail)
4. Atualize SMTP_PASSWORD no .env
5. Reinicie: docker-compose restart airflow-scheduler
```

### DAG não aparece no Airflow
**Problema:** Erro de sintaxe ou imports
**Solução:**
```bash
# Ver erros de import
docker exec -it airflow-webserver airflow dags list-import-errors

# Reiniciar scheduler
docker-compose restart airflow-scheduler

# Ver logs do scheduler
docker-compose logs airflow-scheduler | tail -50
```

### Porta 8080 já em uso
**Problema:** Outro serviço usando a porta
**Solução:**
```bash
# Ver o que está usando a porta
sudo lsof -i :8080

# Parar o serviço conflitante ou mudar porta no docker-compose.yml:
# ports:
#   - "8081:8080"  # Muda porta externa para 8081
```

### Email não chegou
**Problema:** Pode estar no spam ou SMTP errado
**Solução:**
```
1. Verifique pasta de spam
2. Confirme RECIPIENT_EMAILS no .env
3. Veja logs: docker-compose logs | grep "Email sent"
4. Teste SMTP manualmente (código no final deste README)
```

### Containers reiniciando
**Problema:** Erro de configuração
**Solução:**
```bash
# Ver status dos containers
docker-compose ps

# Ver logs do container com problema
docker-compose logs <nome-do-container>

# Verificar se .env está correto
cat .env
```

---

## Banco de Dados

### Schema (4 tabelas)

**1. news_articles**
```sql
- id (serial)
- url (unique) - URL do artigo
- portal - Nome do portal
- title - Título
- content - Conteúdo extraído
- published_date - Data de publicação
- collected_at - Quando foi coletado
- html_s3_key - Chave do HTML no MinIO
```

**2. news_summaries**
```sql
- id (serial)
- summary_date (unique) - Data do resumo
- summary_text - Texto do resumo
- news_count - Quantidade de notícias
- s3_key - Chave do resumo no MinIO
```

**3. email_logs**
```sql
- id (serial)
- summary_id - Referência ao resumo
- recipient_email - Email destinatário
- sent_at - Quando foi enviado
- status - 'sent' ou 'failed'
```

**4. email_preferences**
```sql
- id (serial)
- email (unique) - Email do usuário
- subscribed - TRUE/FALSE
- preferred_time - '07:00' ou '18:00'
- created_at - Quando se inscreveu
- updated_at - Última atualização
```

### Queries Úteis

```sql
-- Ver artigos coletados hoje
SELECT portal, COUNT(*)
FROM news_articles
WHERE DATE(collected_at) = CURRENT_DATE
GROUP BY portal;

-- Ver últimos resumos
SELECT summary_date, news_count, LEFT(summary_text, 100)
FROM news_summaries
ORDER BY summary_date DESC
LIMIT 5;

-- Ver preferências de usuários
SELECT email, subscribed, preferred_time
FROM email_preferences;

-- Ver emails enviados hoje
SELECT recipient_email, sent_at, status
FROM email_logs
WHERE DATE(sent_at) = CURRENT_DATE;
```

---

## Custos e Performance

### Custos OpenAI

**Modelo:** GPT-4o-mini
- Input: $0.15 por 1M tokens
- Output: $0.60 por 1M tokens

**Estimativa por execução:**
- ~2.500 tokens por resumo
- Custo: ~$0.003-0.005 (~R$0.01-0.03)

**Mensal (2x/dia):**
- 60 execuções/mês
- Custo: ~$0.30 (~R$1.50-3.00)

**Conclusão:** $5 duram ~4-6 meses

### Performance

- **Crawling:** ~10-15s por portal
- **Sumarização:** ~15-20s (OpenAI)
- **Total por execução:** ~3-5 minutos
- **Armazenamento:** ~50MB/mês (artigos + resumos)

---

## Variáveis de Ambiente

### Referência Completa (.env)

```env
# ============================================
# AIRFLOW
# ============================================
AIRFLOW_UID=50000
AIRFLOW__CORE__EXECUTOR=LocalExecutor
AIRFLOW__CORE__LOAD_EXAMPLES=False
AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION=True

# ============================================
# POSTGRESQL
# ============================================
POSTGRES_USER=airflow
POSTGRES_PASSWORD=airflow
POSTGRES_DB=news_db
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# ============================================
# MINIO (Object Storage)
# ============================================
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
MINIO_ENDPOINT=minio:9000
MINIO_BUCKET_NAME=news-storage
MINIO_USE_SSL=False

# ============================================
# OPENAI (OBRIGATÓRIO CONFIGURAR)
# ============================================
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o-mini

# ============================================
# EMAIL SMTP (OBRIGATÓRIO CONFIGURAR)
# ============================================
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu-email@gmail.com
SMTP_PASSWORD=abcd efgh ijkl mnop
SMTP_USE_TLS=True
RECIPIENT_EMAILS=email1@empresa.com,email2@empresa.com

# ============================================
# APLICAÇÃO
# ============================================
NEWS_THEME=economia
NEWS_MAX_AGE_HOURS=24
SUMMARY_MAX_NEWS=20
ENABLE_EMAIL_NOTIFICATIONS=True
ENABLE_FAILURE_ALERTS=True

# Chave secreta para tokens de cancelamento
UNSUBSCRIBE_SECRET=your-secret-key-change-me-in-production

# URL base para links de preferências
APP_BASE_URL=http://localhost:5000
```

---

## Testes

### Executar Testes Unitários

```bash
# Instalar dependências de teste
pip install pytest pytest-mock

# Executar todos os testes
pytest tests/

# Executar com verbose
pytest tests/ -v

# Executar testes específicos
pytest tests/test_crawlers.py -v
```

### Testar Crawlers Manualmente

```bash
# Testar IstoÉDinheiro
make crawl-test-istoe

# Testar MoneyTimes
make crawl-test-moneytimes
```

### Testar Conexão SMTP

```python
# Script de teste
python3 << 'EOF'
import smtplib
import os
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

msg = MIMEText("Email de teste do News Summarizer")
msg['Subject'] = 'Teste APS - News Summarizer'
msg['From'] = os.getenv('SMTP_USER')
msg['To'] = os.getenv('SMTP_USER')

server = smtplib.SMTP(os.getenv('SMTP_HOST'), int(os.getenv('SMTP_PORT')))
server.starttls()
server.login(os.getenv('SMTP_USER'), os.getenv('SMTP_PASSWORD'))
server.send_message(msg)
server.quit()

print("✅ Email de teste enviado com sucesso!")
EOF
```

---

## Arquitetura Técnica

### Design Patterns Aplicados

1. **Template Method** - BaseCrawler define estrutura, subclasses implementam detalhes
2. **Repository Pattern** - NewsDatabase abstrai acesso aos dados
3. **Factory Pattern** - Criação de crawlers específicos
4. **Strategy Pattern** - Múltiplas estratégias de parsing

### Decisões Arquiteturais

**Por que Airflow?**
- Orquestração visual de tasks
- Retry automático
- Monitoramento integrado
- Escalabilidade

**Por que PostgreSQL + MinIO?**
- PostgreSQL: Metadados estruturados, queries rápidas
- MinIO: HTML completo (blobs grandes), compatível S3

**Por que GPT-4o-mini?**
- Custo 60x menor que GPT-4
- Qualidade suficiente para resumos
- Latência baixa (~15s)

**Por que Flask separado?**
- Desacopla web app do Airflow
- Pode escalar independentemente
- Deploy simplificado

### Escalabilidade

**Atual (single-node):**
- Suporta até 10 portais
- ~100 artigos/dia
- Custos: ~$5/mês

**Escala horizontal (se necessário):**
- Airflow: CeleryExecutor + múltiplos workers
- PostgreSQL: Réplicas de leitura
- MinIO: Cluster mode
- Custos: ~$50-100/mês (cloud)

---

## Melhorias Futuras

### Roadmap

- [ ] Adicionar mais portais de notícias
- [ ] Suporte a múltiplos temas (tecnologia, política, etc)
- [ ] Dashboard web com métricas
- [ ] API REST para consulta de resumos
- [ ] Notificações push (Telegram/Slack)
- [ ] Análise de sentimento
- [ ] Detecção de trending topics
- [ ] Export para PDF
- [ ] Modo dark no email
- [ ] Testes end-to-end automatizados

### Personalizações Possíveis

**Adicionar novo portal:**
1. Criar `src/crawlers/novo_portal_crawler.py` herdando de `BaseCrawler`
2. Implementar `extract_article_urls()` e `extract_article_data()`
3. Adicionar task no DAG

**Mudar tema das notícias:**
```env
NEWS_THEME=tecnologia  # ou política, esportes, etc
```

**Ajustar criatividade do resumo:**
Editar `src/llm/summarizer.py`:
```python
temperature=0.3  # Mais factual
temperature=0.9  # Mais criativo
```

**Mudar tamanho do resumo:**
```python
max_tokens=1000  # Resumo curto
max_tokens=2000  # Resumo longo
```

---

## Segurança

### Boas Práticas Implementadas

- ✅ Variáveis de ambiente (não hardcoded)
- ✅ Tokens SHA-256 para links de cancelamento
- ✅ .gitignore configurado (não expõe .env)
- ✅ SMTP com TLS
- ✅ SQL injection prevention (prepared statements)
- ✅ Rate limiting no crawling

### Recomendações Adicionais

- Rotacionar API keys periodicamente
- Usar secrets manager em produção (AWS Secrets, HashiCorp Vault)
- Implementar rate limiting na web app
- Adicionar CAPTCHA no unsubscribe
- HTTPS obrigatório em produção

---

## Licença

Projeto acadêmico - Engenharia de Dados - APS 01

---

## Autor

Gabriel Hermida
Insper - Engenharia de Computação
2025
