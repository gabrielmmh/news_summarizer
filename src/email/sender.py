"""Email sender for news summaries."""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from datetime import datetime
import logging
from jinja2 import Environment, FileSystemLoader
import markdown

logger = logging.getLogger(__name__)


class EmailSender:
    """Email sender for news summaries."""

    def __init__(self):
        """Initialize the email sender."""
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.smtp_user = os.getenv('SMTP_USER')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.use_tls = os.getenv('SMTP_USE_TLS', 'True').lower() == 'true'

        # Alternative: Resend API
        self.resend_api_key = os.getenv('RESEND_API_KEY')

        if not self.smtp_user and not self.resend_api_key:
            raise ValueError("Either SMTP_USER or RESEND_API_KEY must be set")

        # Setup Jinja2 template engine
        template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir))

    def _convert_markdown_to_html(self, markdown_text: str) -> str:
        """
        Convert markdown text to HTML.

        Args:
            markdown_text: Markdown text

        Returns:
            HTML text
        """
        return markdown.markdown(
            markdown_text,
            extensions=['extra', 'nl2br', 'sane_lists']
        )

    def _render_template(
        self,
        summary_text: str,
        news_count: int,
        theme: str,
        date_str: str
    ) -> str:
        """
        Render email template with data.

        Args:
            summary_text: Summary text (markdown format)
            news_count: Number of news articles
            theme: News theme
            date_str: Date string

        Returns:
            Rendered HTML
        """
        template = self.jinja_env.get_template('news_digest.html')

        # Convert markdown summary to HTML
        summary_html = self._convert_markdown_to_html(summary_text)

        return template.render(
            summary_html=summary_html,
            news_count=news_count,
            theme=theme.title(),
            date=date_str,
            generated_at=datetime.now().strftime('%d/%m/%Y às %H:%M')
        )

    def send_via_smtp(
        self,
        recipients: List[str],
        subject: str,
        html_content: str
    ) -> bool:
        """
        Send email via SMTP.

        Args:
            recipients: List of recipient emails
            subject: Email subject
            html_content: HTML content

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.smtp_user
            msg['To'] = ', '.join(recipients)

            # Attach HTML content
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)

            # Connect to SMTP server
            if self.use_tls:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)

            # Login and send
            server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.smtp_user, recipients, msg.as_string())
            server.quit()

            logger.info(f"Email sent to {len(recipients)} recipients via SMTP")
            return True

        except Exception as e:
            logger.error(f"Error sending email via SMTP: {e}")
            return False

    def send_via_resend(
        self,
        recipients: List[str],
        subject: str,
        html_content: str
    ) -> bool:
        """
        Send email via Resend API.

        Args:
            recipients: List of recipient emails
            subject: Email subject
            html_content: HTML content

        Returns:
            True if successful, False otherwise
        """
        try:
            import resend

            resend.api_key = self.resend_api_key

            for recipient in recipients:
                resend.Emails.send({
                    "from": self.smtp_user or "noreply@example.com",
                    "to": recipient,
                    "subject": subject,
                    "html": html_content
                })

            logger.info(f"Email sent to {len(recipients)} recipients via Resend")
            return True

        except Exception as e:
            logger.error(f"Error sending email via Resend: {e}")
            return False

    def send_summary_email(
        self,
        recipients: List[str],
        summary_text: str,
        news_count: int,
        theme: str,
        date_str: Optional[str] = None
    ) -> bool:
        """
        Send news summary email to recipients.

        Args:
            recipients: List of recipient emails
            summary_text: Summary text (markdown format)
            news_count: Number of news articles
            theme: News theme
            date_str: Date string (defaults to today)

        Returns:
            True if successful, False otherwise
        """
        if not recipients:
            logger.warning("No recipients specified")
            return False

        # Use today's date if not specified
        if not date_str:
            date_str = datetime.now().strftime('%d/%m/%Y')

        # Render email template
        html_content = self._render_template(
            summary_text=summary_text,
            news_count=news_count,
            theme=theme,
            date_str=date_str
        )

        # Email subject
        subject = f"📰 Resumo de Notícias - {theme.title()} - {date_str}"

        # Send via appropriate method
        if self.resend_api_key:
            return self.send_via_resend(recipients, subject, html_content)
        else:
            return self.send_via_smtp(recipients, subject, html_content)

    def send_failure_notification(
        self,
        recipients: List[str],
        task_name: str,
        error_message: str
    ) -> bool:
        """
        Send failure notification email.

        Args:
            recipients: List of recipient emails
            task_name: Name of failed task
            error_message: Error message

        Returns:
            True if successful, False otherwise
        """
        subject = f"⚠️ Falha no Pipeline de Notícias - {task_name}"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #d9534f;">⚠️ Falha no Pipeline de Notícias</h2>
            <p><strong>Task:</strong> {task_name}</p>
            <p><strong>Data/Hora:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
            <div style="background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 4px; padding: 15px; margin-top: 20px;">
                <p style="margin: 0;"><strong>Erro:</strong></p>
                <pre style="margin: 10px 0 0 0; white-space: pre-wrap;">{error_message}</pre>
            </div>
            <p style="margin-top: 20px; color: #666;">
                Por favor, verifique os logs do Airflow para mais detalhes.
            </p>
        </body>
        </html>
        """

        if self.resend_api_key:
            return self.send_via_resend(recipients, subject, html_content)
        else:
            return self.send_via_smtp(recipients, subject, html_content)


if __name__ == '__main__':
    # Test email sender
    sender = EmailSender()

    test_summary = """# Resumo de Notícias - Economia

## Destaques do Dia
- Mercado financeiro em alta
- Novas políticas econômicas

## Economia Nacional
Texto sobre economia...

## Mercado Internacional
Texto sobre mercado..."""

    # Test with environment variable recipients
    recipients = os.getenv('RECIPIENT_EMAILS', 'test@example.com').split(',')

    success = sender.send_summary_email(
        recipients=recipients,
        summary_text=test_summary,
        news_count=15,
        theme='economia'
    )

    print(f"Email sending {'succeeded' if success else 'failed'}")
