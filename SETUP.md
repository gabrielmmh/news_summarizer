# Guia de Configuração

Instruções completas para configurar OpenAI e SMTP.

## Configuração OpenAI

### 1. Criar Conta

1. Acesse https://platform.openai.com/signup
2. Cadastre-se (pode usar conta Google)
3. Verifique seu email

### 2. Adicionar Créditos

A OpenAI requer créditos para usar a API.

1. Acesse https://platform.openai.com/account/billing
2. Clique em "Add payment method"
3. Adicione cartão de crédito
4. Adicione **$5 USD** (suficiente para meses)

**Custos**:
- Input: $0.15 por 1M tokens
- Output: $0.60 por 1M tokens
- Por execução: ~$0.02-0.03
- $5 dura ~150-200 dias

### 3. Gerar Chave API

1. Acesse https://platform.openai.com/api-keys
2. Clique em "Create new secret key"
3. Nome: `news-summarizer-aps01`
4. **Copie a chave agora** (não poderá ver depois)

Formato: `sk-proj-xxxxxxxxx...`

### 4. Configurar no Projeto

```bash
cd aps01
cp .env.example .env
nano .env
```

Edite:
```env
OPENAI_API_KEY=sk-proj-sua-chave-completa-aqui
OPENAI_MODEL=gpt-4o-mini
```

### 5. Testar Conexão

```bash
pip install openai python-dotenv

python3 << 'EOF'
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Diga olá!"}],
    max_tokens=50
)

print("✅ OpenAI configurado corretamente!")
print(f"Resposta: {response.choices[0].message.content}")
print(f"Tokens usados: {response.usage.total_tokens}")
EOF
```

Saída esperada:
```
✅ OpenAI configurado corretamente!
Resposta: Olá! Como posso ajudar?
Tokens usados: 15
```

## Configuração Gmail SMTP

### 1. Ativar Verificação em Duas Etapas

1. Acesse https://myaccount.google.com/security
2. Encontre "Verificação em duas etapas"
3. Ative a verificação

### 2. Gerar Senha de Aplicativo

1. Acesse https://myaccount.google.com/apppasswords
2. Nome do app: "APS News Summarizer"
3. Clique em "Gerar"
4. Copie a senha de 16 caracteres

### 3. Configurar no Projeto

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu-email@gmail.com
SMTP_PASSWORD=abcd-efgh-ijkl-mnop
SMTP_USE_TLS=True
RECIPIENT_EMAILS=gestor1@empresa.com,gestor2@empresa.com
```

### 4. Testar Envio

```bash
python3 << 'EOF'
import smtplib
from email.mime.text import MIMEText

msg = MIMEText("Teste do sistema")
msg['Subject'] = 'Teste APS'
msg['From'] = 'seu-email@gmail.com'
msg['To'] = 'seu-email@gmail.com'

server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('seu-email@gmail.com', 'sua-senha-app')
server.send_message(msg)
server.quit()

print("✅ Email enviado com sucesso!")
EOF
```

## Problemas Comuns

### OpenAI: "Invalid API Key"

**Causa**: Chave incorreta ou expirada

**Solução**:
- Verifique se copiou a chave completa
- Deve começar com `sk-proj-`
- Gere nova chave se necessário

### OpenAI: "You exceeded your quota"

**Causa**: Sem créditos na conta

**Solução**:
- Adicione créditos: https://platform.openai.com/billing
- Mínimo $5
- Aguarde 1-2 minutos após adicionar

### OpenAI: "Rate limit exceeded"

**Causa**: Muitas requisições em pouco tempo

**Solução**:
- Aguarde 60 segundos
- Tier gratuito: 3 requisições/minuto

### Gmail: "Authentication failed"

**Causa**: Senha incorreta ou 2FA não ativo

**Solução**:
- Ativar verificação em duas etapas primeiro
- Usar senha de aplicativo (16 caracteres)
- Não usar senha normal do Gmail

### Gmail: "Username and Password not accepted"

**Causa**: Tentando usar senha normal

**Solução**:
- Sempre usar senha de aplicativo
- Não usar "acesso menos seguro" (deprecated)

## Variáveis de Ambiente

Referência completa do arquivo `.env`:

```env
# Airflow
AIRFLOW_UID=50000
AIRFLOW__CORE__EXECUTOR=LocalExecutor
AIRFLOW__CORE__LOAD_EXAMPLES=False

# PostgreSQL
POSTGRES_USER=airflow
POSTGRES_PASSWORD=airflow
POSTGRES_DB=news_db
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
MINIO_ENDPOINT=minio:9000
MINIO_BUCKET_NAME=news-storage

# OpenAI (OBRIGATÓRIO)
OPENAI_API_KEY=sk-proj-xxxxxxxx
OPENAI_MODEL=gpt-4o-mini

# Email (OBRIGATÓRIO)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=email@gmail.com
SMTP_PASSWORD=senha-app-16-chars
SMTP_USE_TLS=True
RECIPIENT_EMAILS=email1@empresa.com,email2@empresa.com

# Aplicação
NEWS_THEME=economia
NEWS_MAX_AGE_HOURS=24
SUMMARY_MAX_NEWS=20
ENABLE_EMAIL_NOTIFICATIONS=True
ENABLE_FAILURE_ALERTS=True
```

## Segurança

### Boas Práticas

- ✅ Nunca commitar arquivo `.env`
- ✅ Rotacionar chaves periodicamente
- ✅ Usar variáveis de ambiente
- ✅ Deletar chaves não usadas

### Evitar

- ❌ Hardcoded no código
- ❌ Compartilhar publicamente
- ❌ Commitar no Git
- ❌ Usar em código frontend

## Monitoramento de Custos

### Dashboard OpenAI

https://platform.openai.com/usage
- Ver uso diário
- Configurar alertas
- Acompanhar gastos

### Via Logs do Projeto

```bash
docker-compose logs | grep "Tokens used"
```

Exemplo de saída:
```
Tokens used: 2347 (prompt: 1892, completion: 455)
```

### Calcular Custo

```
Custo = (tokens_prompt × $0.15/1M) + (tokens_completion × $0.60/1M)

Exemplo (2347 tokens):
= (1892 × 0.15/1000000) + (455 × 0.60/1000000)
= $0.00028 + $0.00027
= $0.00055 (~R$0.003 por execução)
```

## Dicas de Economia

1. Usar GPT-4o-mini (não GPT-4)
2. Limitar `max_tokens` (já configurado em 1500)
3. Executar 1x por dia
4. Truncar notícias muito longas (já implementado)

## Otimizar Qualidade

Editar `src/llm/summarizer.py`:

```python
# Resumo mais factual
temperature=0.3

# Resumo mais criativo
temperature=0.9

# Resumo menor (economiza)
max_tokens=1000

# Resumo maior (mais completo)
max_tokens=2000
```

## Próximos Passos

Após configurar:

1. Execute `docker-compose up -d`
2. Aguarde 2 minutos
3. Acesse http://localhost:8080
4. Ative o DAG
5. Trigger manual
6. Confira email em ~5min

---

Problemas? Veja [README.md](README.md) ou [ARCHITECTURE.md](ARCHITECTURE.md)
