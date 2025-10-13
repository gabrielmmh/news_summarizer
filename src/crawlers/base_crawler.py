"""Base crawler class for news portals."""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseCrawler(ABC):
    """Abstract base class for news crawlers."""

    def __init__(self, portal_name: str, base_url: str, timeout: int = 10):
        """
        Initialize the crawler.

        Args:
            portal_name: Name of the news portal
            base_url: Base URL of the portal
            timeout: Request timeout in seconds
        """
        self.portal_name = portal_name
        self.base_url = base_url
        self.timeout = timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                         '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

    def fetch_html(self, url: str) -> Optional[str]:
        """
        Fetch HTML content from a URL.

        Args:
            url: URL to fetch

        Returns:
            HTML content as string or None if failed
        """
        try:
            logger.info(f"Fetching {url}")
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def parse_html(self, html: str) -> BeautifulSoup:
        """
        Parse HTML content.

        Args:
            html: HTML content as string

        Returns:
            BeautifulSoup object
        """
        return BeautifulSoup(html, 'lxml')

    @abstractmethod
    def extract_article_urls(self, soup: BeautifulSoup) -> List[str]:
        """
        Extract article URLs from the homepage.

        Args:
            soup: BeautifulSoup object of the homepage

        Returns:
            List of article URLs
        """
        pass

    @abstractmethod
    def extract_article_data(self, url: str, soup: BeautifulSoup) -> Optional[Dict]:
        """
        Extract article data from an article page.

        Args:
            url: Article URL
            soup: BeautifulSoup object of the article page

        Returns:
            Dictionary with article data or None if failed
        """
        pass

    def crawl_homepage(self) -> List[str]:
        """
        Crawl the homepage and extract article URLs.

        Returns:
            List of article URLs
        """
        html = self.fetch_html(self.base_url)
        if not html:
            return []

        soup = self.parse_html(html)
        urls = self.extract_article_urls(soup)

        logger.info(f"Found {len(urls)} articles on {self.portal_name}")
        return urls

    def crawl_article(self, url: str) -> Optional[Dict]:
        """
        Crawl a single article and extract its data.

        Args:
            url: Article URL

        Returns:
            Dictionary with article data or None if failed
        """
        html = self.fetch_html(url)
        if not html:
            return None

        soup = self.parse_html(html)
        article_data = self.extract_article_data(url, soup)

        if article_data:
            article_data['portal'] = self.portal_name
            article_data['url'] = url
            article_data['collected_at'] = datetime.now()
            article_data['html_raw'] = html

        return article_data

    def crawl_all(self, max_articles: Optional[int] = None, delay: float = 1.0) -> List[Dict]:
        """
        Crawl all articles from the homepage.

        Args:
            max_articles: Maximum number of articles to crawl (None for all)
            delay: Delay between requests in seconds

        Returns:
            List of article data dictionaries
        """
        urls = self.crawl_homepage()

        if max_articles:
            urls = urls[:max_articles]

        articles = []
        for i, url in enumerate(urls, 1):
            logger.info(f"Crawling article {i}/{len(urls)}: {url}")
            article_data = self.crawl_article(url)

            if article_data:
                articles.append(article_data)

            # Be respectful with the server
            if i < len(urls):
                time.sleep(delay)

        logger.info(f"Successfully crawled {len(articles)} articles from {self.portal_name}")
        return articles

    def normalize_url(self, url: str) -> str:
        """
        Normalize a URL (handle relative URLs, etc).

        Args:
            url: URL to normalize

        Returns:
            Normalized URL
        """
        if url.startswith('http'):
            return url
        elif url.startswith('//'):
            return 'https:' + url
        elif url.startswith('/'):
            return self.base_url.rstrip('/') + url
        else:
            return self.base_url.rstrip('/') + '/' + url
