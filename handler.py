"""AWS Lambda handler: fetch single-day OHLCV from yfinance."""
import json
import math
from datetime import datetime, timedelta

import yfinance as yf


def _resolve_isins(isins):
    tickers = {}
    for isin in isins:
        try:
            tickers[isin] = yf.Ticker(isin).info['symbol']
        except Exception:
            tickers[isin] = 'NONE'
    return tickers


def _fetch_ohlcv(symbol, start_date, end_date):
    if symbol == 'NONE':
        return {}
    try:
        data = yf.download(
            symbol,
            start=str(start_date.date()),
            end=str(end_date.date()),
            progress=False,
            auto_adjust=False,
        )
        if data.empty:
            return {}

        if hasattr(data.columns, 'levels'):
            data.columns = data.columns.droplevel(1)

        row = json.loads(json.dumps(list(data.T.to_dict().values())))[0]

        values = [row.get(k) for k in ('Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume')]
        if any(v is None or math.isnan(float(v)) for v in values):
            return {}

        return {
            'open': row['Open'],
            'high': row['High'],
            'low': row['Low'],
            'close': row['Close'],
            'adj_close': row['Adj Close'],
            'volume': row['Volume'],
        }
    except Exception:
        return {}


def _resp(status, body):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def lambda_handler(event, context):
    payload = json.loads(event['body']) if isinstance(event.get('body'), str) else event

    try:
        start_date = datetime.strptime(payload['date'], '%Y-%m-%d')
        end_date = start_date + timedelta(days=1)

        response = {}
        if 'isins' in payload:
            for isin, symbol in _resolve_isins(payload['isins']).items():
                response[isin] = _fetch_ohlcv(symbol, start_date, end_date)
        elif 'tickers' in payload:
            for ticker in payload['tickers']:
                response[ticker] = _fetch_ohlcv(ticker, start_date, end_date)
        else:
            return _resp(400, {"error": "Provide 'isins' or 'tickers'"})

        return _resp(200, response)
    except Exception as e:
        return _resp(500, {"error": str(e)})
