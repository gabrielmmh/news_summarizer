"""
Airflow DAG for news summarization pipeline.

This DAG:
1. Crawls news from multiple portals
2. Stores news in database and MinIO
3. Generates summary using LLM
4. Sends email to subscribers
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.task_group import TaskGroup
import os
import sys
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.crawlers import IstoeDinheiroCrawler, MoneyTimesCrawler
from src.utils import NewsDatabase, MinIOStorage
from src.llm import NewsSummarizer
from src.email import EmailSender

logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv('/opt/airflow/.env')


# Default arguments
default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}


def crawl_istoe_dinheiro(**context):
    """Crawl IstoÉDinheiro portal."""
    logger.info("Starting IstoÉDinheiro crawler")

    try:
        crawler = IstoeDinheiroCrawler()
        articles = crawler.crawl_all(max_articles=15, delay=2.0)

        logger.info(f"Crawled {len(articles)} articles from IstoÉDinheiro")

        # Store in XCom for next tasks
        context['ti'].xcom_push(key='istoe_articles', value=articles)

        return len(articles)

    except Exception as e:
        logger.error(f"Error crawling IstoÉDinheiro: {e}")
        raise


def crawl_moneytimes(**context):
    """Crawl MoneyTimes portal."""
    logger.info("Starting MoneyTimes crawler")

    try:
        crawler = MoneyTimesCrawler()
        articles = crawler.crawl_all(max_articles=15, delay=2.0)

        logger.info(f"Crawled {len(articles)} articles from MoneyTimes")

        # Store in XCom for next tasks
        context['ti'].xcom_push(key='moneytimes_articles', value=articles)

        return len(articles)

    except Exception as e:
        logger.error(f"Error crawling MoneyTimes: {e}")
        raise


def validate_articles(**context):
    """Validate collected articles."""
    logger.info("Validating articles")

    ti = context['ti']

    # Get articles from XCom
    istoe_articles = ti.xcom_pull(key='istoe_articles', task_ids='crawling_group.crawl_istoe')
    moneytimes_articles = ti.xcom_pull(key='moneytimes_articles', task_ids='crawling_group.crawl_moneytimes')

    all_articles = (istoe_articles or []) + (moneytimes_articles or [])

    # Validation rules
    valid_articles = []
    for article in all_articles:
        # Check required fields
        if not article.get('title') or not article.get('content'):
            logger.warning(f"Skipping article without title/content: {article.get('url')}")
            continue

        # Check content length
        if len(article.get('content', '')) < 100:
            logger.warning(f"Skipping article with short content: {article.get('url')}")
            continue

        # Check URL
        if not article.get('url') or not article['url'].startswith('http'):
            logger.warning(f"Skipping article with invalid URL: {article.get('url')}")
            continue

        valid_articles.append(article)

    logger.info(f"Validated {len(valid_articles)} out of {len(all_articles)} articles")

    # Store valid articles in XCom
    ti.xcom_push(key='valid_articles', value=valid_articles)

    return len(valid_articles)


def store_articles(**context):
    """Store articles in database and MinIO."""
    logger.info("Storing articles")

    ti = context['ti']
    articles = ti.xcom_pull(key='valid_articles', task_ids='validate_articles')

    if not articles:
        logger.warning("No articles to store")
        return 0

    # Initialize storage
    storage = MinIOStorage()
    db = NewsDatabase()

    try:
        db.connect()

        stored_count = 0
        for article in articles:
            # Upload HTML to MinIO
            html_raw = article.pop('html_raw', None)
            if html_raw:
                s3_key = storage.upload_html(
                    article['url'],
                    html_raw,
                    article['portal']
                )
                article['html_s3_key'] = s3_key

            # Insert into database
            article_id = db.insert_article(article)
            if article_id:
                stored_count += 1

        logger.info(f"Stored {stored_count} articles")
        return stored_count

    finally:
        db.disconnect()


def generate_summary(**context):
    """Generate summary using LLM."""
    logger.info("Generating summary")

    ti = context['ti']
    articles = ti.xcom_pull(key='valid_articles', task_ids='validate_articles')

    if not articles:
        logger.warning("No articles to summarize")
        return None

    # Initialize summarizer
    summarizer = NewsSummarizer()

    # Generate summary
    summary_text = summarizer.summarize(
        articles,
        max_articles=int(os.getenv('SUMMARY_MAX_NEWS', 20))
    )

    if not summary_text:
        raise ValueError("Failed to generate summary")

    logger.info(f"Generated summary with {len(summary_text)} characters")

    # Store summary
    storage = MinIOStorage()
    db = NewsDatabase()

    try:
        db.connect()

        # Upload summary to MinIO
        today = datetime.now().date()
        s3_key = storage.upload_summary(summary_text, today.isoformat())

        # Store in database
        summary_data = {
            'summary_date': today,
            'summary_text': summary_text,
            'news_count': len(articles),
            'theme': os.getenv('NEWS_THEME', 'economia'),
            's3_key': s3_key
        }

        summary_id = db.insert_summary(summary_data)

        # Store in XCom for email task
        ti.xcom_push(key='summary_text', value=summary_text)
        ti.xcom_push(key='summary_id', value=summary_id)
        ti.xcom_push(key='news_count', value=len(articles))

        logger.info(f"Stored summary with ID {summary_id}")
        return summary_id

    finally:
        db.disconnect()


def send_emails(**context):
    """Send summary emails to subscribers."""
    logger.info("Sending emails")

    # Check if email notifications are enabled
    if os.getenv('ENABLE_EMAIL_NOTIFICATIONS', 'True').lower() != 'true':
        logger.info("Email notifications disabled")
        return 0

    ti = context['ti']

    # Get summary from XCom
    summary_text = ti.xcom_pull(key='summary_text', task_ids='generate_summary')
    summary_id = ti.xcom_pull(key='summary_id', task_ids='generate_summary')
    news_count = ti.xcom_pull(key='news_count', task_ids='generate_summary')

    if not summary_text:
        logger.warning("No summary to send")
        return 0

    # Get recipients
    recipients_str = os.getenv('RECIPIENT_EMAILS', '')
    if not recipients_str:
        logger.warning("No recipients configured")
        return 0

    recipients = [email.strip() for email in recipients_str.split(',') if email.strip()]

    # Initialize email sender
    sender = EmailSender()
    db = NewsDatabase()

    try:
        db.connect()

        # Send email
        success = sender.send_summary_email(
            recipients=recipients,
            summary_text=summary_text,
            news_count=news_count,
            theme=os.getenv('NEWS_THEME', 'economia')
        )

        # Log email sending
        for recipient in recipients:
            db.log_email_sent(
                summary_id=summary_id,
                recipient=recipient,
                status='sent' if success else 'failed'
            )

        if success:
            logger.info(f"Sent emails to {len(recipients)} recipients")
        else:
            logger.error("Failed to send emails")
            raise ValueError("Email sending failed")

        return len(recipients)

    finally:
        db.disconnect()


def send_failure_alert(**context):
    """Send failure notification."""
    logger.info("Sending failure alert")

    # Check if failure alerts are enabled
    if os.getenv('ENABLE_FAILURE_ALERTS', 'True').lower() != 'true':
        logger.info("Failure alerts disabled")
        return

    # Get recipients
    recipients_str = os.getenv('RECIPIENT_EMAILS', '')
    if not recipients_str:
        logger.warning("No recipients configured for alerts")
        return

    recipients = [email.strip() for email in recipients_str.split(',') if email.strip()]

    # Get task instance information
    ti = context['ti']
    dag_run = context['dag_run']

    # Initialize email sender
    sender = EmailSender()

    try:
        sender.send_failure_notification(
            recipients=recipients,
            task_name=ti.task_id,
            error_message=f"DAG Run: {dag_run.run_id}\nExecution Date: {context['execution_date']}"
        )

        logger.info("Sent failure alert")

    except Exception as e:
        logger.error(f"Failed to send failure alert: {e}")


# Create DAG
with DAG(
    'news_summarizer_daily',
    default_args=default_args,
    description='Daily news summarization pipeline',
    schedule_interval='0 7 * * *',  # Run daily at 7 AM
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['news', 'ml', 'summarization'],
) as dag:

    start = EmptyOperator(task_id='start')

    # Crawling tasks (run in parallel)
    with TaskGroup('crawling_group') as crawling_group:
        crawl_istoe = PythonOperator(
            task_id='crawl_istoe',
            python_callable=crawl_istoe_dinheiro,
        )

        crawl_moneytimes = PythonOperator(
            task_id='crawl_moneytimes',
            python_callable=crawl_moneytimes,
        )

    # Validation task
    validate = PythonOperator(
        task_id='validate_articles',
        python_callable=validate_articles,
    )

    # Storage task
    store = PythonOperator(
        task_id='store_articles',
        python_callable=store_articles,
    )

    # Summary generation task
    summarize = PythonOperator(
        task_id='generate_summary',
        python_callable=generate_summary,
    )

    # Email sending task
    send_email = PythonOperator(
        task_id='send_emails',
        python_callable=send_emails,
    )

    # Failure notification task
    failure_alert = PythonOperator(
        task_id='failure_alert',
        python_callable=send_failure_alert,
        trigger_rule='one_failed',  # Run if any upstream task fails
    )

    end = EmptyOperator(task_id='end')

    # Define task dependencies
    start >> crawling_group >> validate >> store >> summarize >> send_email >> end

    # Failure alert runs in case of failures
    [crawling_group, validate, store, summarize, send_email] >> failure_alert
