-- Create news database (only if it doesn't exist)
SELECT 'CREATE DATABASE news_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'news_db')\gexec

-- Connect to news_db
\c news_db;

-- Create news_articles table
CREATE TABLE IF NOT EXISTS news_articles (
    id SERIAL PRIMARY KEY,
    url VARCHAR(1024) UNIQUE NOT NULL,
    portal VARCHAR(100) NOT NULL,
    title TEXT,
    content TEXT,
    published_date TIMESTAMP,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT FALSE,
    html_s3_key VARCHAR(512),
    CONSTRAINT unique_url UNIQUE(url)
);

-- Create news_summaries table
CREATE TABLE IF NOT EXISTS news_summaries (
    id SERIAL PRIMARY KEY,
    summary_date DATE UNIQUE NOT NULL,
    summary_text TEXT NOT NULL,
    news_count INTEGER,
    theme VARCHAR(100),
    s3_key VARCHAR(512),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create email_logs table
CREATE TABLE IF NOT EXISTS email_logs (
    id SERIAL PRIMARY KEY,
    summary_id INTEGER REFERENCES news_summaries(id),
    recipient_email VARCHAR(255) NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'sent',
    error_message TEXT
);

-- Create email_preferences table
CREATE TABLE IF NOT EXISTS email_preferences (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    subscribed BOOLEAN DEFAULT TRUE,
    preferred_time VARCHAR(5) DEFAULT '07:00', -- '07:00' or '18:00'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_news_articles_portal ON news_articles(portal);
CREATE INDEX IF NOT EXISTS idx_news_articles_date ON news_articles(published_date);
CREATE INDEX IF NOT EXISTS idx_news_articles_processed ON news_articles(processed);
CREATE INDEX IF NOT EXISTS idx_news_summaries_date ON news_summaries(summary_date);
CREATE INDEX IF NOT EXISTS idx_email_logs_summary ON email_logs(summary_id);

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE news_db TO airflow;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO airflow;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO airflow;
