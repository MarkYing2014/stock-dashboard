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
    allow_origins=["*"],  # Allow all origins temporarily for testing
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

@app.get("/healthz")
async def healthcheck():
    return {"status": "healthy"}

@app.get("/")
async def root():
    return HTMLResponse(content="""
    <html>
        <head>
            <title>Stock Dashboard API</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                h1 { color: #333; }
                .endpoint { margin: 20px 0; padding: 10px; background: #f5f5f5; border-radius: 5px; }
            </style>
        </head>
        <body>
            <h1>Stock Dashboard API Documentation</h1>
            <div class="endpoint">
                <h3>GET /stocks</h3>
                <p>Returns real-time data for predefined stocks</p>
            </div>
            <div class="endpoint">
                <h3>GET /stock/{ticker}/chart</h3>
                <p>Returns historical chart data for a specific stock</p>
            </div>
            <div class="endpoint">
                <h3>GET /healthz</h3>
                <p>Health check endpoint</p>
            </div>
        </body>
    </html>
    """)

@app.get("/stocks")
def get_stocks():
    try:
        stocks_data = []
        for ticker in TICKERS:
            stock_info = get_stock_data(ticker)
            stocks_data.append(stock_info)
        return JSONResponse(content=stocks_data)
    except Exception as e:
        logger.error(f"Error fetching stocks data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stock/{ticker}/chart")
def get_stock_chart(ticker: str, period: str = "1mo"):
    try:
        stock = yf.Ticker(ticker)
        history = stock.history(period=period)
        
        chart_data = []
        for index, row in history.iterrows():
            chart_data.append({
                "date": index.strftime("%Y-%m-%d"),
                "open": round(row["Open"], 2),
                "high": round(row["High"], 2),
                "low": round(row["Low"], 2),
                "close": round(row["Close"], 2),
                "volume": int(row["Volume"])
            })
        
        return JSONResponse(content=chart_data)
    except Exception as e:
        logger.error(f"Error fetching chart data for {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            stocks_data = []
            for ticker in TICKERS:
                stock_info = get_stock_data(ticker)
                stocks_data.append(stock_info)
            await websocket.send_json(stocks_data)
            await asyncio.sleep(5)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await websocket.close()
