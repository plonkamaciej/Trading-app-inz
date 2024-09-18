from flask import Blueprint, request, jsonify
import yfinance as yf
import threading

get_historical_data_bp = Blueprint('get_historical_data', __name__)

@get_historical_data_bp.route('/get_historical_data', methods=['GET'])
def get_historical_data():
    stock_symbol = request.args.get('stock_symbol')
    timeframe = request.args.get('timeframe', '1mo')  # Default to 1 month if not provided

    if not stock_symbol:
        return jsonify({"error": "Missing stock_symbol"}), 400

    try:
        period, interval = map_timeframe(timeframe)

        # Fetch historical data using yfinance with timeout
        hist = fetch_yfinance_data(stock_symbol, period, interval)

        if hist is None:
            return jsonify({"error": "Request timed out."}), 504
        elif hist.empty:
            return jsonify({"error": f"No historical data available for {stock_symbol} with interval {interval}."}), 404

        # Limit the number of data points to prevent excessive data
        if len(hist) > 1000:
            hist = hist.iloc[-1000:]

        # Prepare data for JSON response
        historical_prices = []
        for date, row in hist.iterrows():
            historical_prices.append({
                "date": date.strftime('%Y-%m-%dT%H:%M:%S'),
                "open": round(row['Open'], 2),
                "high": round(row['High'], 2),
                "low": round(row['Low'], 2),
                "close": round(row['Close'], 2),
                "volume": int(row['Volume'])
            })

        return jsonify({"historical_prices": historical_prices})

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to fetch historical data for {stock_symbol}: {str(e)}"}), 500

def fetch_yfinance_data(stock_symbol, period, interval, timeout=10):
    result = {}
    error = None

    def target():
        try:
            ticker = yf.Ticker(stock_symbol)
            result['hist'] = ticker.history(period=period, interval=interval)
        except Exception as e:
            result['error'] = str(e)

    thread = threading.Thread(target=target)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        return None  # Timeout occurred
    if 'error' in result:
        raise Exception(result['error'])
    return result.get('hist')

def map_timeframe(timeframe):
    timeframe_mapping = {
        '5m': ('7d', '5m'),
        '15m': ('14d', '15m'),
        '30m': ('30d', '30m'),
        '60m': ('60d', '60m'),
        '1d': ('6mo', '1d'),
        '5d': ('1y', '5d'),
        '1mo': ('1y', '1wk'),
        '3mo': ('3y', '1mo'),
        '6mo': ('5y', '1mo'),
        'ytd': ('ytd', '1d'),
        '1y': ('1y', '1wk'),
        '2y': ('2y', '1wk'),
        '5y': ('5y', '1mo'),
        'max': ('max', '1mo'),
    }

    if timeframe in timeframe_mapping:
        period, interval = timeframe_mapping[timeframe]
        validate_period_interval(period, interval)
        return period, interval
    else:
        raise ValueError("Invalid timeframe.")

def validate_period_interval(period, interval):
    valid_combinations = {
        '1m': ['1d'],
        '2m': ['1d'],
        '5m': ['1d', '5d', '7d'],
        '15m': ['1d', '5d', '7d', '14d'],
        '30m': ['1d', '5d', '7d', '14d', '30d'],
        '60m': ['1d', '5d', '7d', '30d', '60d'],
        '90m': ['60d'],
        '1h': ['60d'],
        '1d': ['1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'max'],
        '5d': ['6mo', '1y', '2y', '5y', '10y', 'max'],
        '1wk': ['1y', '2y', '5y', '10y', 'max'],
        '1mo': ['3y', '5y', '10y', 'max'],
    }

    if interval not in valid_combinations:
        raise ValueError(f"Invalid interval '{interval}'.")

    if period not in valid_combinations[interval]:
        raise ValueError(f"Invalid period '{period}' for interval '{interval}'.")
