from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import asyncio
import json
from datetime import datetime, timedelta
import pandas as pd

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local development
        "https://stock-dashboard-frontend.vercel.app",  # Replace with your Vercel domain
    ],
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
    stocks_data = []
    for ticker in TICKERS:
        try:
            stock_data = get_stock_data(ticker)
            stocks_data.append(stock_data)
        except Exception as e:
            print(f"Error fetching data for {ticker}: {str(e)}")
    
    return stocks_data

@app.get("/api/stock/{ticker}/chart")
async def get_stock_chart(ticker: str, period: str = "1mo"):
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
        return {"error": str(e)}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            stocks_data = await get_stocks()
            await websocket.send_json(stocks_data)
            await asyncio.sleep(5)  # Update every 5 seconds
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
    finally:
        await websocket.close()
