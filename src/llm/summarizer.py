"""LLM-based news summarization using OpenAI."""
import os
from typing import List, Dict, Optional
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)


class NewsSummarizer:
    """News summarizer using OpenAI GPT-4o-mini."""

    def __init__(self):
        """Initialize the summarizer with OpenAI."""
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self.theme = os.getenv('NEWS_THEME', 'economia')

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set in environment")

        # Initialize OpenAI client
        self.client = OpenAI(api_key=self.api_key)
        logger.info(f"Initialized OpenAI summarizer with model: {self.model}")

    def _prepare_news_context(self, articles: List[Dict], max_articles: int = 20) -> str:
        """
        Prepare news articles for summarization.

        Args:
            articles: List of article dictionaries
            max_articles: Maximum number of articles to include

        Returns:
            Formatted news context string
        """
        # Sort by date (most recent first)
        sorted_articles = sorted(
            articles[:max_articles],
            key=lambda x: x.get('published_date', ''),
            reverse=True
        )

        context_parts = []
        for i, article in enumerate(sorted_articles, 1):
            title = article.get('title', 'Sem título')
            content = article.get('content', '')
            portal = article.get('portal', 'Desconhecido')
            date = article.get('published_date', '')

            # Truncate content if too long
            max_content_length = 500
            if len(content) > max_content_length:
                content = content[:max_content_length] + '...'

            context_parts.append(
                f"[Notícia {i}]\n"
                f"Portal: {portal}\n"
                f"Data: {date}\n"
                f"Título: {title}\n"
                f"Conteúdo: {content}\n"
            )

        return '\n---\n'.join(context_parts)

    def _build_prompt(self, news_context: str) -> str:
        """
        Build the summarization prompt.

        Args:
            news_context: Formatted news context

        Returns:
            Complete prompt string
        """
        base_prompt = f"""Você é um assistente especializado em análise de notícias para executivos e gestores.

Sua tarefa é criar um resumo executivo das principais notícias do dia no tema: {self.theme}.

NOTÍCIAS DO DIA:
{news_context}

INSTRUÇÕES:
1. Crie um resumo executivo profissional e conciso
2. Organize as informações por temas relevantes (ex: mercado financeiro, empresas, economia global)
3. Destaque os pontos mais importantes e suas implicações
4. Use bullet points para facilitar a leitura
5. Mantenha um tom objetivo e informativo
6. Limite o resumo a aproximadamente 500-700 palavras

FORMATO DO RESUMO:
# Resumo de Notícias - {self.theme.title()}

## Destaques do Dia
[Principais acontecimentos em 2-3 bullet points]

## [Tema 1]
[Resumo das notícias relacionadas]

## [Tema 2]
[Resumo das notícias relacionadas]

## Implicações e Tendências
[Análise das implicações e tendências observadas]

---
Elabore o resumo agora:"""

        return base_prompt

    def summarize(self, articles: List[Dict], max_articles: int = 20) -> Optional[str]:
        """
        Generate a summary of news articles using OpenAI.

        Args:
            articles: List of article dictionaries
            max_articles: Maximum number of articles to summarize

        Returns:
            Summary text or None if failed
        """
        if not articles:
            logger.warning("No articles to summarize")
            return None

        logger.info(f"Summarizing {len(articles)} articles using OpenAI {self.model}")

        try:
            # Prepare context
            news_context = self._prepare_news_context(articles, max_articles)
            prompt = self._build_prompt(news_context)

            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um assistente especializado em resumir notícias para executivos."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=1500
            )

            summary = response.choices[0].message.content

            # Log token usage for cost tracking
            usage = response.usage
            logger.info(
                f"Summary generated successfully. "
                f"Tokens used: {usage.total_tokens} "
                f"(prompt: {usage.prompt_tokens}, completion: {usage.completion_tokens})"
            )

            return summary

        except Exception as e:
            logger.error(f"Error generating summary with OpenAI: {e}")
            return None


if __name__ == '__main__':
    # Test the summarizer
    test_articles = [
        {
            'title': 'Teste de Notícia 1',
            'content': 'Conteúdo da notícia 1 sobre economia.',
            'portal': 'Portal Teste',
            'published_date': '2024-01-15',
        },
        {
            'title': 'Teste de Notícia 2',
            'content': 'Conteúdo da notícia 2 sobre finanças.',
            'portal': 'Portal Teste',
            'published_date': '2024-01-15',
        }
    ]

    summarizer = NewsSummarizer()
    summary = summarizer.summarize(test_articles)

    if summary:
        print("Summary generated successfully!")
        print(summary)
    else:
        print("Failed to generate summary")
