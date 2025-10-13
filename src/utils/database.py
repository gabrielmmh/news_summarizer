"""Database utilities for storing news data."""
import os
from typing import List, Dict, Optional
from datetime import datetime, date
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
import logging

logger = logging.getLogger(__name__)


class NewsDatabase:
    """Database manager for news data."""

    def __init__(self):
        """Initialize database connection."""
        self.conn_params = {
            'host': os.getenv('POSTGRES_HOST', 'postgres'),
            'port': int(os.getenv('POSTGRES_PORT', 5432)),
            'user': os.getenv('POSTGRES_USER', 'airflow'),
            'password': os.getenv('POSTGRES_PASSWORD', 'airflow'),
            'database': os.getenv('POSTGRES_DB', 'news_db')
        }
        self.conn = None

    def connect(self):
        """Establish database connection."""
        try:
            self.conn = psycopg2.connect(**self.conn_params)
            logger.info("Connected to database")
        except psycopg2.Error as e:
            logger.error(f"Database connection error: {e}")
            raise

    def disconnect(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Disconnected from database")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

    def insert_article(self, article: Dict) -> Optional[int]:
        """
        Insert a news article into the database.

        Args:
            article: Article data dictionary

        Returns:
            Article ID if successful, None otherwise
        """
        try:
            with self.conn.cursor() as cur:
                query = """
                    INSERT INTO news_articles (url, portal, title, content, published_date, html_s3_key)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (url) DO UPDATE
                    SET title = EXCLUDED.title,
                        content = EXCLUDED.content,
                        published_date = EXCLUDED.published_date,
                        html_s3_key = EXCLUDED.html_s3_key
                    RETURNING id
                """
                cur.execute(query, (
                    article['url'],
                    article['portal'],
                    article['title'],
                    article['content'],
                    article['published_date'],
                    article.get('html_s3_key')
                ))
                article_id = cur.fetchone()[0]
                self.conn.commit()
                logger.info(f"Inserted article {article_id}: {article['title']}")
                return article_id
        except psycopg2.Error as e:
            logger.error(f"Error inserting article: {e}")
            self.conn.rollback()
            return None

    def insert_articles_batch(self, articles: List[Dict]) -> int:
        """
        Insert multiple articles in a batch.

        Args:
            articles: List of article dictionaries

        Returns:
            Number of articles inserted
        """
        if not articles:
            return 0

        try:
            with self.conn.cursor() as cur:
                query = """
                    INSERT INTO news_articles (url, portal, title, content, published_date, html_s3_key)
                    VALUES %s
                    ON CONFLICT (url) DO UPDATE
                    SET title = EXCLUDED.title,
                        content = EXCLUDED.content,
                        published_date = EXCLUDED.published_date,
                        html_s3_key = EXCLUDED.html_s3_key
                """
                values = [
                    (
                        article['url'],
                        article['portal'],
                        article['title'],
                        article['content'],
                        article['published_date'],
                        article.get('html_s3_key')
                    )
                    for article in articles
                ]
                execute_values(cur, query, values)
                self.conn.commit()
                logger.info(f"Inserted {len(articles)} articles")
                return len(articles)
        except psycopg2.Error as e:
            logger.error(f"Error inserting articles batch: {e}")
            self.conn.rollback()
            return 0

    def get_unprocessed_articles(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Get unprocessed articles from the database.

        Args:
            limit: Maximum number of articles to retrieve

        Returns:
            List of article dictionaries
        """
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = """
                    SELECT * FROM news_articles
                    WHERE processed = FALSE
                    ORDER BY published_date DESC
                """
                if limit:
                    query += f" LIMIT {limit}"

                cur.execute(query)
                articles = cur.fetchall()
                return [dict(article) for article in articles]
        except psycopg2.Error as e:
            logger.error(f"Error fetching unprocessed articles: {e}")
            return []

    def get_recent_articles(self, hours: int = 24, limit: Optional[int] = None) -> List[Dict]:
        """
        Get recent articles from the database.

        Args:
            hours: Number of hours to look back
            limit: Maximum number of articles to retrieve

        Returns:
            List of article dictionaries
        """
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = """
                    SELECT * FROM news_articles
                    WHERE collected_at >= NOW() - INTERVAL '%s hours'
                    ORDER BY published_date DESC
                """
                if limit:
                    query += f" LIMIT {limit}"

                cur.execute(query, (hours,))
                articles = cur.fetchall()
                return [dict(article) for article in articles]
        except psycopg2.Error as e:
            logger.error(f"Error fetching recent articles: {e}")
            return []

    def mark_article_processed(self, article_id: int):
        """
        Mark an article as processed.

        Args:
            article_id: Article ID
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "UPDATE news_articles SET processed = TRUE WHERE id = %s",
                    (article_id,)
                )
                self.conn.commit()
        except psycopg2.Error as e:
            logger.error(f"Error marking article as processed: {e}")
            self.conn.rollback()

    def insert_summary(self, summary_data: Dict) -> Optional[int]:
        """
        Insert a news summary into the database.

        Args:
            summary_data: Summary data dictionary

        Returns:
            Summary ID if successful, None otherwise
        """
        try:
            with self.conn.cursor() as cur:
                query = """
                    INSERT INTO news_summaries (summary_date, summary_text, news_count, theme, s3_key)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (summary_date) DO UPDATE
                    SET summary_text = EXCLUDED.summary_text,
                        news_count = EXCLUDED.news_count,
                        theme = EXCLUDED.theme,
                        s3_key = EXCLUDED.s3_key
                    RETURNING id
                """
                cur.execute(query, (
                    summary_data['summary_date'],
                    summary_data['summary_text'],
                    summary_data['news_count'],
                    summary_data.get('theme'),
                    summary_data.get('s3_key')
                ))
                summary_id = cur.fetchone()[0]
                self.conn.commit()
                logger.info(f"Inserted summary {summary_id}")
                return summary_id
        except psycopg2.Error as e:
            logger.error(f"Error inserting summary: {e}")
            self.conn.rollback()
            return None

    def get_summary_by_date(self, summary_date: date) -> Optional[Dict]:
        """
        Get summary for a specific date.

        Args:
            summary_date: Date to get summary for

        Returns:
            Summary dictionary or None
        """
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM news_summaries WHERE summary_date = %s",
                    (summary_date,)
                )
                result = cur.fetchone()
                return dict(result) if result else None
        except psycopg2.Error as e:
            logger.error(f"Error fetching summary: {e}")
            return None

    def log_email_sent(self, summary_id: int, recipient: str, status: str = 'sent', error: Optional[str] = None):
        """
        Log email sending status.

        Args:
            summary_id: Summary ID
            recipient: Recipient email
            status: Sending status
            error: Error message if failed
        """
        try:
            with self.conn.cursor() as cur:
                query = """
                    INSERT INTO email_logs (summary_id, recipient_email, status, error_message)
                    VALUES (%s, %s, %s, %s)
                """
                cur.execute(query, (summary_id, recipient, status, error))
                self.conn.commit()
        except psycopg2.Error as e:
            logger.error(f"Error logging email: {e}")
            self.conn.rollback()
