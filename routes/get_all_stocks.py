from flask import Blueprint, request, jsonify
from supabase_client import get_from_supabase
from config import SUPABASE_URL, HEADERS

get_all_stocks_bp = Blueprint('get_all_stocks', __name__)

@get_all_stocks_bp.route('/get_all_stocks', methods=['GET'])
def get_all_stocks():
    user_id = request.args.get('user_id')

    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400

    # Fetch portfolio associated with the user
    portfolio_response = get_from_supabase('portfolios', params={'user_id': f'eq.{user_id}'})
    if portfolio_response.status_code != 200:
        return jsonify({"error": "Failed to fetch portfolio", "details": portfolio_response.json()}), portfolio_response.status_code

    portfolios = portfolio_response.json()

    if not portfolios:
        return jsonify({"error": "No portfolio found for user"}), 404

    portfolio_id = portfolios[0].get('portfolio_id')

    # Fetch all stocks in the portfolio
    stocks_response = get_from_supabase('portfolio_stocks', params={'portfolio_id': f'eq.{portfolio_id}'})
    if stocks_response.status_code != 200:
        return jsonify({"error": "Failed to fetch stocks", "details": stocks_response.json()}), stocks_response.status_code

    stocks = stocks_response.json()

    if not stocks:
        return jsonify({"error": "No stocks found in portfolio"}), 404

    owned_stocks = []

    for stock in stocks:
        stock_symbol = stock.get('stock_symbol')
        quantity = stock.get('quantity')
        average_price = stock.get('average_price')

        # Get current stock price from the database


        current_value = quantity * average_price

        owned_stocks.append({
            "stock_symbol": stock_symbol,
            "quantity": quantity,
            "average_price": average_price,
            "value" : current_value

        })

    return jsonify({"owned_stocks": owned_stocks})

def get_current_stock_price(stock_symbol):
    # Fetch current stock price from the database
    response = get_from_supabase('stock_prices', params={'stock_symbol': f'eq.{stock_symbol}'})
    if response.status_code != 200:
        print(f"Error fetching stock price for {stock_symbol}: {response.json()}")
        return None

    price_data = response.json()
    if price_data:
        return price_data[0].get('current_price')

    return None
