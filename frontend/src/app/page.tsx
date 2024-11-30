'use client';

import { useEffect, useState, useRef } from 'react';
import { Card, Title, Text } from '@tremor/react';
import { ComposedChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Line } from 'recharts';
import { ArrowDownIcon, ArrowUpIcon } from 'lucide-react';

// Custom candlestick component
interface CandlestickProps {
  x: number;
  y: number;
  width: number;
  height: number;
  open: number;
  close: number;
  high: number;
  low: number;
}

const CustomCandlestick = (props: CandlestickProps) => {
  const { x, y, width, height, open, close, high, low } = props;
  const isGreen = close > open;
  const color = isGreen ? '#22c55e' : '#ef4444';
  const bodyHeight = Math.abs(open - close);
  const bodyY = isGreen ? close : open;

  return (
    <g>
      {/* Wick */}
      <line
        x1={x + width / 2}
        y1={y + height - high}
        x2={x + width / 2}
        y2={y + height - low}
        stroke={color}
        strokeWidth={1}
      />
      {/* Body */}
      <rect
        x={x}
        y={y + height - bodyY}
        width={width}
        height={bodyHeight}
        fill={color}
      />
    </g>
  );
};

interface StockData {
  symbol: string;
  currentValue: number;
  previousClose: number;
  change: number;
  changePct: number;
  volume: number;
  marketCap: number;
  peRatio: number;
  eps: number;
}

interface ChartData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  ma: number;
}

interface PeriodMetrics {
  lowestVolume: number;
  highestVolume: number;
  lowestPrice: number;
  highestPrice: number;
  averageVolume: number;
  currentMarketCap: number;
}

export default function Home() {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const [stocks, setStocks] = useState<StockData[]>([]);
  const [selectedStock, setSelectedStock] = useState<string>('HII');
  const [chartData, setChartData] = useState<ChartData[]>([]);
  const [periodMetrics, setPeriodMetrics] = useState<PeriodMetrics>({
    lowestVolume: 0,
    highestVolume: 0,
    lowestPrice: 0,
    highestPrice: 0,
    averageVolume: 0,
    currentMarketCap: 0
  });

  useEffect(() => {
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws';
    const ws = new WebSocket(wsUrl);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setStocks(data);
    };

    return () => ws.close();
  }, []);

  useEffect(() => {
    const fetchChartData = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(`${apiUrl}/stock/${selectedStock}/chart`);
        const data = await response.json();
        
        // Calculate moving average for trend line
        const period = 5; // 5-day moving average
        const prices = data.prices;
        const ma = prices.map((_: number, index: number) => {
          if (index < period - 1) return null;
          const slice = prices.slice(index - period + 1, index + 1);
          return slice.reduce((a: number, b: number) => a + b, 0) / period;
        });

        const formattedData = data.dates.map((date: string, index: number) => ({
          date,
          open: data.prices[Math.max(0, index - 1)], // Using previous close as open
          high: data.prices[index] * 1.002, // Simulating high
          low: data.prices[index] * 0.998, // Simulating low
          close: data.prices[index],
          volume: data.volumes[index],
          ma: ma[index]
        }));
        
        setChartData(formattedData);
      } catch (error) {
        console.error('Error fetching chart data:', error);
      }
    };

    if (selectedStock) {
      fetchChartData();
    }
  }, [selectedStock]);

  useEffect(() => {
    const fetchStocks = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(`${apiUrl}/stocks`);
        const data = await response.json();
        setStocks(data);
      } catch (error) {
        console.error('Error fetching stocks:', error);
      }
    };

    fetchStocks();
    const interval = setInterval(fetchStocks, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const calculatePeriodMetrics = (data: ChartData[]) => {
      if (data.length === 0) return;
      
      const volumes = data.map(d => d.volume);
      const prices = data.map(d => d.close);
      
      setPeriodMetrics({
        lowestVolume: Math.min(...volumes),
        highestVolume: Math.max(...volumes),
        lowestPrice: Math.min(...prices),
        highestPrice: Math.max(...prices),
        averageVolume: Math.floor(volumes.reduce((a, b) => a + b, 0) / volumes.length),
        currentMarketCap: stocks.find(s => s.symbol === selectedStock)?.marketCap || 0
      });
    };

    if (chartData.length > 0) {
      calculatePeriodMetrics(chartData);
    }
  }, [chartData, selectedStock, stocks]);

  return (
    <main className="p-4 md:p-10 mx-auto max-w-7xl">
      <Title className="chart-title">Stocks Dashboard</Title>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-4">
        {stocks.map((stock) => (
          <Card
            key={stock.symbol}
            className="cursor-pointer hover:shadow-lg transition-shadow"
            onClick={() => setSelectedStock(stock.symbol)}
          >
            <div className="flex justify-between items-start">
              <div>
                <Text className="stock-symbol">{stock.symbol}</Text>
                <Title className="stock-price">${stock.currentValue.toFixed(2)}</Title>
              </div>
              <div className="flex items-center">
                {stock.change >= 0 ? (
                  <div className="flex items-center percentage-up">
                    <ArrowUpIcon size={20} />
                    <Text>{stock.changePct.toFixed(2)}%</Text>
                  </div>
                ) : (
                  <div className="flex items-center percentage-down">
                    <ArrowDownIcon size={20} />
                    <Text>{stock.changePct.toFixed(2)}%</Text>
                  </div>
                )}
              </div>
            </div>
          </Card>
        ))}
      </div>

      <Card className="mt-8">
        <Title className="chart-title">Stock Price Trends</Title>
        <div className="h-[500px] mt-4" ref={chartContainerRef}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart
              data={chartData}
              margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis yAxisId="left" orientation="left" domain={['auto', 'auto']} />
              <YAxis 
                yAxisId="right" 
                orientation="right" 
                domain={['auto', 'auto']}
                label={{ value: 'Volume', angle: -90, position: 'insideRight' }}
              />
              <Tooltip 
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    return (
                      <div className="custom-tooltip">
                        <p className="tooltip-date">{payload[0].payload.date}</p>
                        <p className="tooltip-price">Open: ${payload[0].payload.open.toFixed(2)}</p>
                        <p className="tooltip-price">High: ${payload[0].payload.high.toFixed(2)}</p>
                        <p className="tooltip-price">Low: ${payload[0].payload.low.toFixed(2)}</p>
                        <p className="tooltip-price">Close: ${payload[0].payload.close.toFixed(2)}</p>
                        <p className="tooltip-volume">Volume: {payload[0].payload.volume.toLocaleString()}</p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Bar 
                yAxisId="right"
                dataKey="volume" 
                fill="#ff7e67" 
                opacity={0.5}
                name="Volume Traded"
              />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="ma"
                stroke="#2dd4bf"
                dot={false}
                name="MA(5)"
              />
              {chartData.map((entry, index) => {
                const containerWidth = chartContainerRef.current?.clientWidth || 800;
                const candleWidth = Math.max(8, (containerWidth - 100) / chartData.length);
                return (
                  <CustomCandlestick
                    key={`candle-${index}`}
                    x={index * candleWidth}
                    y={0}
                    width={candleWidth * 0.8}
                    height={chartContainerRef.current?.clientHeight || 400}
                    open={entry.open}
                    close={entry.close}
                    high={entry.high}
                    low={entry.low}
                  />
                );
              })}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <Card className="mt-8">
        <Title className="chart-title">Period Metrics</Title>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
          <div className="space-y-4">
            <Card decoration="left" decorationColor="red">
              <Text className="metric-label">Lowest Volume Day Trade</Text>
              <Title className="metric-value">{periodMetrics.lowestVolume.toLocaleString()}</Title>
            </Card>
            <Card decoration="left" decorationColor="red">
              <Text className="metric-label">Lowest Close Price</Text>
              <Title className="metric-value">{periodMetrics.lowestPrice.toFixed(2)} $</Title>
            </Card>
          </div>
          <div className="space-y-4">
            <Card decoration="left" decorationColor="green">
              <Text className="metric-label">Highest Volume Day Trade</Text>
              <Title className="metric-value">{periodMetrics.highestVolume.toLocaleString()}</Title>
            </Card>
            <Card decoration="left" decorationColor="green">
              <Text className="metric-label">Highest Close Price</Text>
              <Title className="metric-value">{periodMetrics.highestPrice.toFixed(2)} $</Title>
            </Card>
          </div>
        </div>
        <div className="mt-4 space-y-4">
          <Card>
            <Text className="metric-label">Average Daily Volume</Text>
            <Title className="metric-value">{periodMetrics.averageVolume.toLocaleString()}</Title>
          </Card>
          <Card>
            <Text className="metric-label">Current Market Cap</Text>
            <Title className="metric-value">{(periodMetrics.currentMarketCap / 1000000000).toFixed(0).toLocaleString()} $</Title>
          </Card>
        </div>
      </Card>
    </main>
  );
}
