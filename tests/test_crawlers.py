"""Tests for news crawlers."""
import pytest
from unittest.mock import Mock, patch
from src.crawlers.base_crawler import BaseCrawler
from src.crawlers.istoe_crawler import IstoeDinheiroCrawler
from src.crawlers.moneytimes_crawler import MoneyTimesCrawler


class TestBaseCrawler:
    """Tests for BaseCrawler."""

    def test_normalize_url_absolute(self):
        """Test URL normalization with absolute URL."""
        crawler = IstoeDinheiroCrawler()
        url = "https://example.com/article"
        assert crawler.normalize_url(url) == url

    def test_normalize_url_relative(self):
        """Test URL normalization with relative URL."""
        crawler = IstoeDinheiroCrawler()
        url = "/article"
        expected = "https://www.istoedinheiro.com.br/article"
        assert crawler.normalize_url(url) == expected

    def test_normalize_url_protocol_relative(self):
        """Test URL normalization with protocol-relative URL."""
        crawler = IstoeDinheiroCrawler()
        url = "//example.com/article"
        assert crawler.normalize_url(url) == "https://example.com/article"


class TestIstoeDinheiroCrawler:
    """Tests for IstoeDinheiroCrawler."""

    def test_initialization(self):
        """Test crawler initialization."""
        crawler = IstoeDinheiroCrawler()
        assert crawler.portal_name == 'IstoÉDinheiro'
        assert 'istoedinheiro.com.br' in crawler.base_url

    @patch('src.crawlers.base_crawler.requests.get')
    def test_fetch_html_success(self, mock_get):
        """Test successful HTML fetch."""
        mock_response = Mock()
        mock_response.text = "<html>Test</html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        crawler = IstoeDinheiroCrawler()
        html = crawler.fetch_html("https://example.com")

        assert html == "<html>Test</html>"
        mock_get.assert_called_once()

    @patch('src.crawlers.base_crawler.requests.get')
    def test_fetch_html_failure(self, mock_get):
        """Test HTML fetch failure."""
        mock_get.side_effect = Exception("Connection error")

        crawler = IstoeDinheiroCrawler()
        html = crawler.fetch_html("https://example.com")

        assert html is None


class TestMoneyTimesCrawler:
    """Tests for MoneyTimesCrawler."""

    def test_initialization(self):
        """Test crawler initialization."""
        crawler = MoneyTimesCrawler()
        assert crawler.portal_name == 'MoneyTimes'
        assert 'moneytimes.com.br' in crawler.base_url


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
