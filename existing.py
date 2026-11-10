from rest_framework.response import Response
from rest_framework.decorators import api_view
import yfinance as yf
import os
import json
from datetime import datetime, timedelta
import math


@api_view(['GET'])
def status_view(request):

    content = {
        "application": "Generate Report from yFinance Service",
        "status": "OK",
        "environment": os.environ['ENV_NAME'],
        "release": os.environ['TAG_NAME'],
        "pipeline": os.environ['CI_PIPELINE_ID']
    }

    return Response(content)


@api_view(['POST'])
def yfinance(request):

    # Convert ISIN's to Tickers

    isins = request.data['isins']

    tickers = {}

    for isin in isins:
        data = yf.Ticker(isin)
        try:
            tickers[isin] = data.info['symbol']
        except:
            tickers[isin] = 'NONE'

    date = request.data['date']

    start_date = datetime.strptime(date, '%Y-%m-%d')
    end_date = start_date + timedelta(days=1)

    response = {}

    # Get Tickers Data

    for ticker in tickers:

        try:
            data = yf.download(tickers[ticker], start=str(start_date.date()), end=str(end_date.date()))
            json_data = json.loads(json.dumps(list(data.T.to_dict().values())))
            json_data = json_data[0]

            if math.isnan(float(json_data['Open'])) or \
                    math.isnan(float(json_data['High'])) or \
                    math.isnan(float(json_data['Low'])) or \
                    math.isnan(float(json_data['Close'])) or \
                    math.isnan(float(json_data['Adj Close'])) or \
                    math.isnan(float(json_data['Volume'])):

                formatted_data = {}

            else:

                # Format Key Data
                formatted_data = {
                    'open': json_data['Open'],
                    'high': json_data['High'],
                    'low': json_data['Low'],
                    'close': json_data['Close'],
                    'adj_close': json_data['Adj Close'],
                    'volume': json_data['Volume']
                }

        except:
            formatted_data = {}

        # Format Json Data
        response[ticker] = formatted_data

    return Response(response)


@api_view(['POST'])
def yfinance_filter(request):

    tickers = request.data['tickers']
    date = request.data['date']

    start_date = datetime.strptime(date, '%Y-%m-%d')
    end_date = start_date + timedelta(days=1)

    response = {}

    for ticker in tickers:
        try:
            data = yf.download(ticker, start=str(start_date.date()), end=str(end_date.date()))
            json_data = json.loads(json.dumps(list(data.T.to_dict().values())))
            json_data = json_data[0]

            if math.isnan(float(json_data['Open'])) or \
                    math.isnan(float(json_data['High'])) or \
                    math.isnan(float(json_data['Low'])) or \
                    math.isnan(float(json_data['Close'])) or \
                    math.isnan(float(json_data['Adj Close'])) or \
                    math.isnan(float(json_data['Volume'])):

                formatted_data = {}

            else:

                formatted_data = {
                    'open': json_data['Open'],
                    'high': json_data['High'],
                    'low': json_data['Low'],
                    'close': json_data['Close'],
                    'adj_close': json_data['Adj Close'],
                    'volume': json_data['Volume']
                }
        except Exception as e:
            print(e)
            formatted_data = {}

        # Format Json Data
        response[ticker] = formatted_data

    return Response(response)

