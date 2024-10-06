from flask import Blueprint, request, jsonify
import yfinance as yf
import logging

# Define the blueprint
stock_price_bp = Blueprint('stock_price', __name__)

# Route for getting the current stock price
@stock_price_bp.route('/get_stock_price', methods=['GET'])
def get_stock_price():
    # Get the stock symbol from query parameters
    stock_symbol = request.args.get('symbol')
    
    if not stock_symbol:
        return jsonify({"error": "Symbol akcji jest wymagany"}), 400

    try:
        # Fetch stock information from yfinance
        stock = yf.Ticker(stock_symbol)
        stock_info = stock.history(period="1d")
        
        # Check if the stock data was retrieved successfully
        if stock_info.empty:
            return jsonify({"error": "Nie udało się pobrać danych akcji"}), 400
        
        # Get the latest closing price
        current_price = stock_info['Close'].iloc[0]
        
        return jsonify({
            "symbol": stock_symbol,
            "price": current_price
        }), 200

    except Exception as e:
        logging.error(f"Error fetching stock price for {stock_symbol}: {e}")
        return jsonify({"error": "Wystąpił błąd podczas pobierania ceny akcji"}), 500
