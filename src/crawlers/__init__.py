"""Crawlers package for news portals."""
from .base_crawler import BaseCrawler
from .istoe_crawler import IstoeDinheiroCrawler
from .moneytimes_crawler import MoneyTimesCrawler

__all__ = ['BaseCrawler', 'IstoeDinheiroCrawler', 'MoneyTimesCrawler']
