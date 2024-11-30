from fastapi import FastAPI, WebSocket, Response, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
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
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
port = int(os.getenv("PORT", 8000))

logger.info(f"Starting server with CORS origins: {origins}")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
        "changePct": round(((history["Close"] - info.get("previousClose", 0)) / info.get("previousClose", 1)) * 100, 2),
        "volume": history["Volume"],
        "marketCap": info.get("marketCap", 0),
        "peRatio": round(info.get("trailingPE", 0), 2),
        "eps": info.get("trailingEps", 0)
    }

@app.get("/")
async def root():
    """API Documentation endpoint"""
    logger.info("Root endpoint accessed")
    return HTMLResponse(content="""
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
            <h2>Available Endpoints:</h2>
            <ul>
                <li><code>GET /stocks</code> - Get real-time stock data</li>
                <li><code>GET /stock/{ticker}/chart</code> - Get historical chart data for a specific stock</li>
                <li><code>WebSocket /ws</code> - Real-time stock updates</li>
            </ul>
            <p>For API documentation, visit <a href="/docs">/docs</a></p>
        </body>
    </html>
    """)

@app.head("/")
async def head():
    """Health check endpoint"""
    logger.info("Health check performed")
    return Response(status_code=200)

@app.get("/stocks")
async def get_stocks():
    """Get real-time stock data for predefined stocks"""
    logger.info("Fetching stock data")
    try:
        stocks_data = []
        for ticker in TICKERS:
            try:
                stock_data = get_stock_data(ticker)
                stocks_data.append(stock_data)
            except Exception as e:
                logger.error(f"Error fetching data for {ticker}: {str(e)}")
        return stocks_data
    except Exception as e:
        logger.error(f"Error fetching stock data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stock/{ticker}/chart")
async def get_stock_chart(ticker: str, period: str = "1mo"):
    """Get historical chart data for a specific stock"""
    logger.info(f"Fetching chart data for {ticker}")
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        
        chart_data = []
        for index, row in df.iterrows():
            chart_data.append({
                "date": index.strftime("%Y-%m-%d"),
                "open": round(row["Open"], 2),
                "high": round(row["High"], 2),
                "low": round(row["Low"], 2),
                "close": round(row["Close"], 2),
                "volume": int(row["Volume"])
            })
        
        return chart_data
    except Exception as e:
        logger.error(f"Error fetching chart data for {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            stocks_data = await get_stocks()
            await websocket.send_text(json.dumps(stocks_data))
            await asyncio.sleep(5)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await websocket.close()
