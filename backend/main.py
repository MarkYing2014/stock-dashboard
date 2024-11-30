from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import yfinance as yf
import json
import asyncio
from typing import List
import os
import logging
from dotenv import load_dotenv
from datetime import datetime, timedelta
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Stock Dashboard API",
    description="API for real-time stock data and charts",
    version="1.0.0"
)

# Get CORS origins from environment variable, fallback to localhost if not set
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
port = int(os.getenv("PORT", 8000))

logger.info(f"Starting server with CORS origins: {cors_origins}")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TICKERS = ["HII", "GD", "TXT", "LDOS", "KTOS", "MRCY", "CW", "HEI", "RCAT", "PLTR"]

def get_stock_data(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info
    history = stock.history(period="1d", interval="1m").iloc[-1]
    
    return {
        "symbol": ticker,
        "currentValue": round(history["Close"], 2),
        "previousClose": round(info.get("previousClose", 0), 2),
        "change": round(history["Close"] - info.get("previousClose", 0), 2),
        "changePct": round(((history["Close"] - info.get("previousClose", 0)) / info.get("previousClose", 0)) * 100, 2),
        "volume": info.get("volume", 0),
        "marketCap": info.get("marketCap", 0),
        "peRatio": info.get("forwardPE", 0),
        "eps": info.get("trailingEps", 0)
    }

@app.get("/api/stocks")
async def get_stocks():
    logger.info("Fetching stocks data")
    stocks_data = []
    for ticker in TICKERS:
        try:
            stock_data = get_stock_data(ticker)
            stocks_data.append(stock_data)
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {str(e)}")
    
    return stocks_data

@app.get("/api/stock/{ticker}/chart")
async def get_stock_chart(ticker: str, period: str = "1mo"):
    logger.info(f"Fetching chart data for {ticker} with period {period}")
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        
        chart_data = {
            "dates": df.index.strftime('%Y-%m-%d').tolist(),
            "prices": df["Close"].round(2).tolist(),
            "volumes": df["Volume"].tolist(),
            "high": df["High"].round(2).tolist(),
            "low": df["Low"].round(2).tolist(),
            "open": df["Open"].round(2).tolist(),
        }
        return chart_data
    except Exception as e:
        logger.error(f"Error fetching chart data for {ticker}: {str(e)}")
        return {"error": str(e)}

@app.get("/", response_class=HTMLResponse)
@app.head("/", response_class=HTMLResponse)
async def root():
    html_content = """
    <html>
        <head>
            <title>Stock Dashboard API</title>
            <style>
                body { font-family: system-ui; max-width: 800px; margin: 0 auto; padding: 20px; }
                code { background: #f4f4f4; padding: 2px 5px; border-radius: 3px; }
            </style>
        </head>
        <body>
            <h1>Stock Dashboard API</h1>
            <p>Available endpoints:</p>
            <ul>
                <li><code>GET /api/stocks</code> - Get real-time data for all stocks</li>
                <li><code>GET /api/stock/{ticker}/chart</code> - Get chart data for a specific stock</li>
                <li><code>WebSocket /ws</code> - Real-time stock updates every 5 seconds</li>
            </ul>
            <p>For API documentation, visit <a href="/docs">/docs</a></p>
        </body>
    </html>
    """
    return html_content

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            stocks_data = await get_stocks()
            await websocket.send_json(stocks_data)
            await asyncio.sleep(5)  # Update every 5 seconds
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        await websocket.close()
