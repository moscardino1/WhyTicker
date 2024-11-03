# app.py
from flask import Flask, render_template, jsonify, request, make_response
import yfinance as yf
from newsapi import NewsApiClient
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from transformers import pipeline
import requests
from flask_cors import CORS
import pandas as pd
from functools import lru_cache

load_dotenv()

app = Flask(__name__)
CORS(app)

# Initialize APIs with error handling
try:
    newsapi = NewsApiClient(api_key=os.getenv('NEWS_API_KEY'))
    sentiment_analyzer = pipeline("sentiment-analysis", 
                                model="ProsusAI/finbert", 
                                device="cpu")
except Exception as e:
    print(f"Error initializing APIs: {e}")

@lru_cache(maxsize=100)
def get_stock_data(ticker, cache_time=300):  # 5 minute cache
    """Cached stock data retrieval with improved efficiency"""
    try:
        stock = yf.Ticker(ticker)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=2)  # Reduced from 7 to 2 days
        
        hist = stock.history(start=start_date, end=end_date, interval='1h')
        if hist.empty or len(hist) < 2:
            return None
            
        latest_data = hist.tail(2)
        current_price = latest_data['Close'].iloc[-1]
        previous_price = latest_data['Close'].iloc[-2]
        
        # Add historical data for the chart
        historical = {
            'timestamps': hist.index.strftime('%Y-%m-%d %H:%M:%S').tolist(),
            'prices': hist['Close'].round(2).tolist()
        }
        
        return {
            'name': stock.info.get('longName', ticker),
            'price': round(current_price, 2),
            'change': round(((current_price - previous_price) / previous_price) * 100, 2),
            'volume': int(latest_data['Volume'].iloc[-1]),
            'historical': historical
        }
    except Exception as e:
        print(f"Error getting stock data for {ticker}: {str(e)}")
        return None

@lru_cache(maxsize=50)
def get_relevant_news(ticker, company_name, cache_time=900):  # 15 minute cache
    """Cached news retrieval with optimized query"""
    try:
        query = f'({company_name} OR {ticker}) AND (stock OR market)'
        news = newsapi.get_everything(
            q=query,
            language='en',
            from_param=(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
            to=datetime.now().strftime('%Y-%m-%d'),
            sort_by='relevancy',
            page_size=3  # Limit initial request to 3 articles
        )
        
        return [{
            'title': article['title'],
            'description': article['description'],
            'url': article['url'],
            'publishedAt': article['publishedAt']  # Add publication date
        } for article in news['articles'] if article.get('description') and article.get('title')]
    except Exception as e:
        print(f"Error getting news for {ticker}: {str(e)}")
        return []

@app.route('/')
def home():
    response = make_response(render_template('index.html'))
    # Update CSP headers to specifically allow cdnjs.cloudflare.com
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
        "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
        "img-src 'self' data: https:; "
        "font-src 'self' https:; "
        "connect-src 'self'"
    )
    return response

@app.route('/analyze/<ticker>')
def analyze(ticker):
    print(f"Analyzing ticker: {ticker}")
    
    if not ticker or len(ticker) > 10:
        return jsonify({'error': 'Invalid ticker format'}), 400
        
    ticker = ticker.upper()
    stock_data = get_stock_data(ticker)
    
    if not stock_data:
        return jsonify({'error': f'Unable to fetch data for {ticker}'}), 404
    
    news = get_relevant_news(ticker, stock_data['name'])
    
    # Only analyze sentiment if we have news
    sentiment = analyze_news_sentiment(news) if news else {"label": "neutral", "score": 0.5}
    
    response_data = {
        'stock': stock_data,
        'news': news,
        'sentiment': sentiment
    }
    
    print(f"Successfully analyzed {ticker}")
    print(f"Response data: {response_data}")
    
    return jsonify(response_data)

def analyze_news_sentiment(news_articles):
    """Analyze news sentiment with better error handling"""
    try:
        if not news_articles:
            return {"label": "neutral", "score": 0.5}
            
        all_text = " ".join([
            f"{article['title']} {article['description']}"
            for article in news_articles
        ])
        
        sentiment = sentiment_analyzer(all_text)[0]
        print(f"Sentiment analysis result: {sentiment}")
        return sentiment
    except Exception as e:
        print(f"Error in sentiment analysis: {str(e)}")
        return {"label": "neutral", "score": 0.5}

if __name__ == '__main__':
    app.run(debug=True)