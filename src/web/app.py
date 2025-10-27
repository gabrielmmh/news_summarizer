"""
Flask web application for managing email subscriptions and preferences.
"""
import os
import hashlib
import urllib.parse
from flask import Flask, request, render_template_string, redirect, url_for
from datetime import datetime
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

# Direct import to avoid loading unnecessary dependencies
import importlib.util
spec = importlib.util.spec_from_file_location("database",
    os.path.join(os.path.dirname(__file__), '../utils/database.py'))
database_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(database_module)
NewsDatabase = database_module.NewsDatabase

app = Flask(__name__)


def verify_token(email: str, token: str) -> bool:
    """
    Verify if the token is valid for the given email.

    Args:
        email: Email address
        token: Token to verify

    Returns:
        True if valid, False otherwise
    """
    secret = os.getenv('UNSUBSCRIBE_SECRET', 'default-secret-key-change-me')
    token_input = f"{email}:{secret}".encode('utf-8')
    expected_token = hashlib.sha256(token_input).hexdigest()[:32]
    return token == expected_token


@app.route('/unsubscribe', methods=['GET', 'POST'])
def unsubscribe():
    """Handle unsubscribe requests."""
    email = request.args.get('email') or request.form.get('email')
    token = request.args.get('token') or request.form.get('token')

    if not email or not token:
        return render_template_string(ERROR_TEMPLATE,
            message="Link inválido. Email ou token não fornecido."), 400

    # Decode email if needed
    email = urllib.parse.unquote(email)

    # Verify token
    if not verify_token(email, token):
        return render_template_string(ERROR_TEMPLATE,
            message="Link inválido ou expirado. Token de segurança incorreto."), 403

    if request.method == 'POST':
        # Process unsubscribe
        db = NewsDatabase()
        try:
            db.connect()
            cursor = db.conn.cursor()

            # Insert into a preferences table (we'll create this)
            cursor.execute("""
                INSERT INTO email_preferences (email, subscribed, updated_at)
                VALUES (%s, FALSE, %s)
                ON CONFLICT (email)
                DO UPDATE SET subscribed = FALSE, updated_at = %s
            """, (email, datetime.now(), datetime.now()))

            db.conn.commit()

            return render_template_string(SUCCESS_UNSUBSCRIBE_TEMPLATE, email=email)

        except Exception as e:
            print(f"Error unsubscribing: {e}")
            return render_template_string(ERROR_TEMPLATE,
                message=f"Erro ao processar cancelamento: {str(e)}"), 500
        finally:
            db.disconnect()

    # Show confirmation page
    return render_template_string(CONFIRM_UNSUBSCRIBE_TEMPLATE, email=email, token=token)


@app.route('/preferences', methods=['GET', 'POST'])
def preferences():
    """Handle email preferences."""
    email = request.args.get('email') or request.form.get('email')
    token = request.args.get('token') or request.form.get('token')

    if not email or not token:
        return render_template_string(ERROR_TEMPLATE,
            message="Link inválido. Email ou token não fornecido."), 400

    # Decode email if needed
    email = urllib.parse.unquote(email)

    # Verify token
    if not verify_token(email, token):
        return render_template_string(ERROR_TEMPLATE,
            message="Link inválido ou expirado. Token de segurança incorreto."), 403

    db = NewsDatabase()
    try:
        db.connect()
        cursor = db.conn.cursor()

        if request.method == 'POST':
            # Get form data
            preferred_time = request.form.get('preferred_time', '07:00')
            subscribed = request.form.get('subscribed') == 'on'

            # Update preferences
            cursor.execute("""
                INSERT INTO email_preferences (email, subscribed, preferred_time, updated_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (email)
                DO UPDATE SET subscribed = %s, preferred_time = %s, updated_at = %s
            """, (email, subscribed, preferred_time, datetime.now(),
                  subscribed, preferred_time, datetime.now()))

            db.conn.commit()

            return render_template_string(SUCCESS_PREFERENCES_TEMPLATE, email=email)

        # Get current preferences
        cursor.execute("""
            SELECT subscribed, preferred_time
            FROM email_preferences
            WHERE email = %s
        """, (email,))

        result = cursor.fetchone()
        if result:
            subscribed, preferred_time = result
        else:
            subscribed, preferred_time = True, '07:00'

        return render_template_string(
            PREFERENCES_TEMPLATE,
            email=email,
            token=token,
            subscribed=subscribed,
            preferred_time=preferred_time
        )

    except Exception as e:
        print(f"Error managing preferences: {e}")
        return render_template_string(ERROR_TEMPLATE,
            message=f"Erro ao carregar preferências: {str(e)}"), 500
    finally:
        db.disconnect()


@app.route('/')
def index():
    """Home page."""
    return render_template_string(HOME_TEMPLATE)


# Shared CSS for all templates
SHARED_CSS = """
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
        max-width: 560px;
        margin: 0 auto;
        padding: 40px 20px;
        background-color: #f7f8fa;
        color: #1f2937;
    }
    .container {
        background: #ffffff;
        padding: 48px;
        border-radius: 3px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        border: 1px solid #e5e7eb;
    }
    .header {
        border-bottom: 3px solid #3b82f6;
        padding-bottom: 16px;
        margin-bottom: 32px;
    }
    .brand {
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        color: #9ca3af;
        margin: 0 0 8px 0;
    }
    h1 {
        color: #111827;
        margin: 0;
        font-size: 28px;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    p {
        line-height: 1.7;
        color: #374151;
        margin: 16px 0;
    }
    .form-group {
        margin: 24px 0;
    }
    label {
        display: block;
        margin-bottom: 8px;
        font-weight: 500;
        font-size: 14px;
        color: #111827;
    }
    select {
        width: 100%;
        padding: 10px 12px;
        border: 1px solid #d1d5db;
        border-radius: 3px;
        font-size: 15px;
        background-color: #ffffff;
        color: #1f2937;
    }
    select:focus {
        outline: none;
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }
    .checkbox-group {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    input[type="checkbox"] {
        width: 18px;
        height: 18px;
        cursor: pointer;
    }
    button {
        background-color: #1a1a1a;
        color: #ffffff;
        border: none;
        padding: 12px 24px;
        border-radius: 3px;
        cursor: pointer;
        font-size: 15px;
        font-weight: 500;
        width: 100%;
        transition: background-color 0.2s;
    }
    button:hover {
        background-color: #374151;
    }
    .info-box {
        background-color: #f0f9ff;
        border-left: 3px solid #3b82f6;
        padding: 16px;
        margin: 24px 0;
        border-radius: 3px;
    }
    .success-box {
        background-color: #f0fdf4;
        border-left: 3px solid #22c55e;
        padding: 16px;
        margin: 24px 0;
        border-radius: 3px;
    }
    .warning-box {
        background-color: #fffbeb;
        border-left: 3px solid #f59e0b;
        padding: 16px;
        margin: 24px 0;
        border-radius: 3px;
    }
    .error-box {
        background-color: #fef2f2;
        border-left: 3px solid #ef4444;
        padding: 16px;
        margin: 24px 0;
        border-radius: 3px;
    }
    a {
        color: #3b82f6;
        text-decoration: none;
    }
    a:hover {
        text-decoration: underline;
    }
    @media (max-width: 600px) {
        body {
            padding: 20px 15px;
        }
        .container {
            padding: 32px 24px;
        }
        h1 {
            font-size: 24px;
        }
    }
"""

# HTML Templates
HOME_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gerenciamento de Assinatura</title>
    <style>
        """ + SHARED_CSS + """
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <p class="brand">News Summarizer</p>
            <h1>Gerenciamento de Assinatura</h1>
        </div>
        <p>Sistema de gerenciamento de emails para resumos diários de notícias.</p>
        <p>Use os links enviados por email para gerenciar suas preferências ou cancelar sua assinatura.</p>
    </div>
</body>
</html>
"""

ERROR_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Erro</title>
    <style>
        """ + SHARED_CSS + """
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <p class="brand">News Summarizer</p>
            <h1>Erro</h1>
        </div>
        <div class="error-box">
            <p style="margin: 0;">{{ message }}</p>
        </div>
        <p><a href="/">Voltar à página inicial</a></p>
    </div>
</body>
</html>
"""

CONFIRM_UNSUBSCRIBE_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cancelar Assinatura</title>
    <style>
        """ + SHARED_CSS + """
        .danger-button {
            background-color: #ef4444;
        }
        .danger-button:hover {
            background-color: #dc2626;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <p class="brand">News Summarizer</p>
            <h1>Cancelar Assinatura</h1>
        </div>
        <div class="warning-box">
            <p><strong>Atenção:</strong> Você está prestes a cancelar sua assinatura do resumo diário de notícias.</p>
            <p style="margin: 8px 0 0 0;">Email: <strong>{{ email }}</strong></p>
        </div>
        <p>Você não receberá mais nossos resumos diários de notícias. Você sempre pode se reinscrever mais tarde.</p>

        <form method="POST">
            <input type="hidden" name="email" value="{{ email }}">
            <input type="hidden" name="token" value="{{ token }}">
            <button type="submit" class="danger-button">Confirmar Cancelamento</button>
        </form>

        <p style="text-align: center; margin-top: 16px;"><a href="/">Manter assinatura e voltar</a></p>
    </div>
</body>
</html>
"""

SUCCESS_UNSUBSCRIBE_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Assinatura Cancelada</title>
    <style>
        """ + SHARED_CSS + """
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <p class="brand">News Summarizer</p>
            <h1>Assinatura Cancelada</h1>
        </div>
        <div class="success-box">
            <p>Sua assinatura foi cancelada com sucesso.</p>
            <p style="margin: 8px 0 0 0;">Email: <strong>{{ email }}</strong></p>
        </div>
        <p>Sentiremos sua falta! Se você mudou de ideia, pode se reinscrever a qualquer momento.</p>
    </div>
</body>
</html>
"""

PREFERENCES_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Preferências de Email</title>
    <style>
        """ + SHARED_CSS + """
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <p class="brand">News Summarizer</p>
            <h1>Preferências de Email</h1>
        </div>

        <div class="info-box">
            <p style="margin: 0;">Email: <strong>{{ email }}</strong></p>
        </div>

        <form method="POST">
            <input type="hidden" name="email" value="{{ email }}">
            <input type="hidden" name="token" value="{{ token }}">

            <div class="form-group">
                <div class="checkbox-group">
                    <input type="checkbox" id="subscribed" name="subscribed"
                           {% if subscribed %}checked{% endif %}>
                    <label for="subscribed" style="margin: 0;">
                        Receber resumos de notícias
                    </label>
                </div>
            </div>

            <div class="form-group">
                <label for="preferred_time">Horário de envio:</label>
                <select id="preferred_time" name="preferred_time">
                    <option value="07:00" {% if preferred_time == '07:00' %}selected{% endif %}>
                        07:00 - Manhã
                    </option>
                    <option value="18:00" {% if preferred_time == '18:00' %}selected{% endif %}>
                        18:00 - Tarde
                    </option>
                </select>
            </div>

            <button type="submit">Salvar Preferências</button>
        </form>
    </div>
</body>
</html>
"""

SUCCESS_PREFERENCES_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Preferências Salvas</title>
    <style>
        """ + SHARED_CSS + """
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <p class="brand">News Summarizer</p>
            <h1>Preferências Salvas</h1>
        </div>
        <div class="success-box">
            <p>Suas preferências foram atualizadas com sucesso!</p>
            <p style="margin: 8px 0 0 0;">Email: <strong>{{ email }}</strong></p>
        </div>
        <p>As alterações serão aplicadas a partir do próximo envio de email.</p>
    </div>
</body>
</html>
"""


if __name__ == '__main__':
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    port = int(os.getenv('WEB_PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
