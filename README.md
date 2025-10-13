# APS 01 - Sumarizador de Notícias

Sistema automático que coleta notícias, gera resumos com IA e distribui por email.

## Stack Tecnológico

- **Airflow** 2.10 - Orquestração
- **PostgreSQL** 15 - Banco de dados
- **MinIO** - Armazenamento de objetos
- **OpenAI** GPT-4o-mini - Sumarização
- **BeautifulSoup** - Web scraping

## Instalação Rápida

### Pré-requisitos

- Docker + Docker Compose
- Chave OpenAI ([como obter](SETUP.md))

### Configuração

```bash
cd aps01
cp .env.example .env
nano .env
```

Configure as seguintes variáveis:
```env
OPENAI_API_KEY=sk-proj-sua-chave-aqui
SMTP_USER=seu-email@gmail.com
SMTP_PASSWORD=senha-app-16-chars
RECIPIENT_EMAILS=gestor@empresa.com
```

### Executar

```bash
docker-compose up -d
```

Após 2 minutos, acesse http://localhost:8080 (airflow/airflow):
1. Ative o DAG `news_summarizer_daily`
2. Clique em "Trigger DAG"
3. Aguarde ~5 minutos
4. Confira seu email!

## Estrutura do Projeto

```
aps01/
├── dags/                   # DAGs do Airflow
├── src/
│   ├── crawlers/          # Coletores de notícias
│   ├── llm/               # Integração OpenAI
│   ├── email/             # Envio de emails
│   └── utils/             # Banco e storage
└── docker-compose.yml
```

## Fluxo do Pipeline

```
[Diariamente às 7h]
    ↓
Coletar notícias (IstoÉDinheiro + MoneyTimes)
    ↓
Validar artigos
    ↓
Salvar (PostgreSQL + MinIO)
    ↓
Gerar resumo (GPT-4o-mini)
    ↓
Enviar emails
```

## Comandos Úteis

```bash
docker-compose up -d        # Iniciar
docker-compose logs -f      # Ver logs
docker-compose down         # Parar
docker-compose down -v      # Limpar tudo
```

## Personalização

### Adicionar Portal

1. Criar `src/crawlers/novo_crawler.py`
2. Herdar de `BaseCrawler`
3. Adicionar task no DAG

### Mudar Tema

```env
NEWS_THEME=tecnologia
```

### Ajustar LLM

Editar `src/llm/summarizer.py`:
```python
temperature=0.7        # 0=factual, 1=criativo
max_tokens=1500        # Tamanho do resumo
```

## Custos

- Por execução: ~R$0.10-0.20
- Por mês: ~R$3-6

## Monitoramento

```bash
# Ver uso de tokens
docker-compose logs | grep "Tokens used"

# Acessar banco
docker exec -it postgres psql -U airflow -d news_db

# Ver storage (MinIO)
# http://localhost:9001 (minioadmin/minioadmin)
```

## Solução de Problemas

### OpenAI não funciona

- Verificar chave no `.env`
- Adicionar créditos: https://platform.openai.com/billing
- Ver guia completo: [SETUP.md](SETUP.md)

### DAG não aparece

```bash
docker exec -it airflow-webserver airflow dags list-import-errors
docker-compose restart airflow-scheduler
```

### Email não envia

- Gmail: usar senha de app
- Testar conexão: `telnet smtp.gmail.com 587`

## Documentação

- **[SETUP.md](SETUP.md)** - Configuração detalhada (OpenAI + SMTP)
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Arquitetura e decisões técnicas

## Requisitos da APS

- ✅ Crawling de 2+ portais
- ✅ Scraping (título, texto, data)
- ✅ Armazenamento estruturado
- ✅ Sumarização com LLM
- ✅ Templates de email
- ✅ DAG do Airflow
- ✅ Agendamento diário

---

*Engenharia de Dados - APS 01*
