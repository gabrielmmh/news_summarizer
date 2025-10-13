"""Crawler for MoneyTimes news portal."""
from typing import List, Dict, Optional
from datetime import datetime
from bs4 import BeautifulSoup
import re
import logging

from .base_crawler import BaseCrawler

logger = logging.getLogger(__name__)


class MoneyTimesCrawler(BaseCrawler):
    """Crawler for MoneyTimes (moneytimes.com.br)."""

    def __init__(self):
        super().__init__(
            portal_name='MoneyTimes',
            base_url='https://www.moneytimes.com.br'
        )

    def extract_article_urls(self, soup: BeautifulSoup) -> List[str]:
        """
        Extract article URLs from MoneyTimes homepage.

        Args:
            soup: BeautifulSoup object of the homepage

        Returns:
            List of article URLs
        """
        urls = []

        # Find all article links
        # MoneyTimes typically uses article tags or specific classes
        article_containers = soup.find_all(['article', 'div'], class_=re.compile(r'.*(post|article|noticia).*', re.I))

        for container in article_containers:
            links = container.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                # Filter for actual article URLs
                if href and (
                    re.search(r'/\d{4}/', href) or  # Contains year
                    'moneytimes.com.br' in href
                ) and not any(x in href for x in ['/categoria/', '/tag/', '/autor/', '#']):
                    normalized_url = self.normalize_url(href)
                    if normalized_url not in urls:
                        urls.append(normalized_url)

        # Alternative: Find links in main content
        if not urls:
            all_links = soup.find_all('a', href=re.compile(r'moneytimes\.com\.br/.*\d{4}'))
            for link in all_links:
                href = link.get('href', '')
                if href:
                    normalized_url = self.normalize_url(href)
                    if normalized_url not in urls:
                        urls.append(normalized_url)

        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in urls:
            if url not in seen and self.base_url in url and len(url.split('/')) > 4:
                seen.add(url)
                unique_urls.append(url)

        return unique_urls[:30]  # Limit to most recent 30 articles

    def extract_article_data(self, url: str, soup: BeautifulSoup) -> Optional[Dict]:
        """
        Extract article data from MoneyTimes article page.

        Args:
            url: Article URL
            soup: BeautifulSoup object of the article page

        Returns:
            Dictionary with article data or None if failed
        """
        try:
            # Extract title
            title = None
            title_selectors = [
                soup.find('h1', class_=re.compile(r'.*(title|titulo|headline).*', re.I)),
                soup.find('h1'),
                soup.find('meta', property='og:title'),
                soup.find('meta', attrs={'name': 'twitter:title'})
            ]

            for selector in title_selectors:
                if selector:
                    if selector.name == 'meta':
                        title = selector.get('content', '')
                    else:
                        title = selector.get_text(strip=True)
                    if title:
                        break

            if not title:
                logger.warning(f"Could not extract title from {url}")
                return None

            # Extract content
            content = None
            content_selectors = [
                soup.find('div', class_=re.compile(r'.*(content|corpo|texto|article-body).*', re.I)),
                soup.find('article'),
                soup.find('div', class_=re.compile(r'.*post.*', re.I)),
                soup.find('div', attrs={'itemprop': 'articleBody'})
            ]

            for selector in content_selectors:
                if selector:
                    # Remove unwanted elements
                    for tag in selector.find_all(['script', 'style', 'iframe', 'aside', 'nav', 'header', 'footer']):
                        tag.decompose()

                    # Remove ads and related content
                    for tag in selector.find_all(class_=re.compile(r'.*(ad|advertisement|related|sidebar).*', re.I)):
                        tag.decompose()

                    paragraphs = selector.find_all('p')
                    if paragraphs:
                        content = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
                        if content:
                            break

            if not content or len(content) < 100:
                logger.warning(f"Could not extract sufficient content from {url}")
                return None

            # Extract date
            published_date = None
            date_selectors = [
                soup.find('time', attrs={'datetime': True}),
                soup.find('meta', property='article:published_time'),
                soup.find('meta', attrs={'name': 'publishdate'}),
                soup.find('span', class_=re.compile(r'.*(date|data).*', re.I))
            ]

            for selector in date_selectors:
                if selector:
                    if selector.name == 'meta':
                        date_str = selector.get('content', '')
                    elif selector.name == 'time':
                        date_str = selector.get('datetime', selector.get_text(strip=True))
                    else:
                        date_str = selector.get_text(strip=True)

                    if date_str:
                        published_date = self._parse_date(date_str)
                        if published_date:
                            break

            return {
                'title': title,
                'content': content,
                'published_date': published_date or datetime.now()
            }

        except Exception as e:
            logger.error(f"Error extracting data from {url}: {e}")
            return None

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse date string to datetime object.

        Args:
            date_str: Date string

        Returns:
            datetime object or None if parsing failed
        """
        # Clean the date string
        date_str = date_str.strip()

        # Common date formats
        date_formats = [
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%d/%m/%Y %H:%M:%S',
            '%d/%m/%Y %H:%M',
            '%d/%m/%Y',
        ]

        for fmt in date_formats:
            try:
                # Handle timezone info
                clean_date = date_str.replace('Z', '+00:00')
                # Try to parse only the relevant part
                if 'T' in clean_date:
                    clean_date = clean_date.split('.')[0]  # Remove milliseconds

                return datetime.strptime(clean_date[:19], fmt[:19])
            except (ValueError, IndexError):
                continue

        logger.warning(f"Could not parse date: {date_str}")
        return None


if __name__ == '__main__':
    # Test the crawler
    crawler = MoneyTimesCrawler()
    print(f"Testing {crawler.portal_name} crawler...")

    urls = crawler.crawl_homepage()
    print(f"Found {len(urls)} articles")

    if urls:
        print(f"\nTesting first article: {urls[0]}")
        article = crawler.crawl_article(urls[0])
        if article:
            print(f"Title: {article.get('title')}")
            print(f"Date: {article.get('published_date')}")
            print(f"Content length: {len(article.get('content', ''))} chars")
