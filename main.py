import requests
import json
from openai import OpenAI
import os
from dotenv import load_dotenv
import sqlite3
from datetime import datetime

load_dotenv()
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")

def fetch_binance_news():
    url = "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageNo=1&pageSize=10"
    try:
        response = requests.get(url)
        data = response.json()
        articles = []
        for catalog in data['data']['catalogs']:
            articles.extend(catalog['articles'])
        return articles
    except Exception as e:
        print(f"Ошибка при получении новостей: {e}")
        return []

def get_article_url(article_code):
    return f"https://www.binance.com/ru/support/announcement/{article_code}"

def init_db():
    conn = sqlite3.connect('news.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS processed_news
                 (id TEXT PRIMARY KEY, title TEXT, processed_at TIMESTAMP)''')
    conn.commit()
    conn.close()

def is_news_processed(news_id):
    conn = sqlite3.connect('news.db')
    c = conn.cursor()
    c.execute("SELECT id FROM processed_news WHERE id = ?", (news_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

def mark_news_as_processed(news_id, title):
    conn = sqlite3.connect('news.db')
    c = conn.cursor()
    c.execute("INSERT INTO processed_news (id, title, processed_at) VALUES (?, ?, ?)",
              (news_id, title, datetime.now()))
    conn.commit()
    conn.close()

def analyze_news_with_ai(title, url):
    prompt = f"""
    Заголовок: {title}
    Ссылка на статью: {url}

    Ответь строго в формате JSON:
    {{
        "impact_score": 0-100,
        "summary": "Краткая суть",
        "urgency": "high/medium/low",
        "reasoning": "Объяснение"
    }}
    """
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        analysis = response.choices[0].message.content
        if (analysis.startswith("```json") and analysis.endswith("```")):
            analysis = analysis[7:-3].strip()
        return json.loads(analysis)
    except Exception as e:
        print(f"Ошибка при анализе ИИ: {e}")
        return {"impact_score": 0, "summary": "Error", "urgency": "low", "reasoning": ""}

def send_telegram_alert(article, analysis):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    article_url = get_article_url(article['code'])
    
    message = f"""
🚨 *ВАЖНАЯ НОВОСТЬ BINANCE* 🚨

*Заголовок:* {article['title']}
*Оценка влияния:* {analysis['impact_score']}/100
*Срочность:* {analysis['urgency']}

*Суть:* {analysis['summary']}

*Обоснование:* {analysis['reasoning']}

[Читать статью]({article_url})
"""
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        request = requests.post(url, json=payload)
        print(request.text)
    except Exception as e:
        print(f"Ошибка при отправке сообщения в Telegram: {e}")

if __name__ == "__main__":
    init_db()
    articles = fetch_binance_news()
    if articles:
        print(f"Найдено {len(articles)} новостей")
        for article in articles:
            article_id = str(article['id'])
            if is_news_processed(article_id):
                continue

            url = get_article_url(article['code'])
            print(f"\n--- Анализ: {article['title']} ---")
            analysis = analyze_news_with_ai(article['title'], url)
            print(f"Impact Score: {analysis['impact_score']}")
            print(f"URL: {url}")
            print(f"Summary: {analysis['summary']}")

            # Если новость важная - отправляем алерт
            if analysis['impact_score'] > 70:
                send_telegram_alert(article, analysis)

            mark_news_as_processed(article_id, article['title'])