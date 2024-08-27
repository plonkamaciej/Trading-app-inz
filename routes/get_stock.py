# routes/get_stock.py

from flask import Blueprint, request, jsonify
from supabase_client import get_from_supabase
from config import TEST_PORTFOLIO_ID

get_stock_bp = Blueprint('get_stock', __name__)

@get_stock_bp.route('/get_stock', methods=['GET'])
def get_stock():
    portfolio_id = request.args.get('portfolio_id', TEST_PORTFOLIO_ID)
    stock_symbol = request.args.get('stock_symbol')

    if not stock_symbol:
        return jsonify({"error": "Missing required field: stock_symbol"}), 400

    response = get_from_supabase(f"portfolio_stocks?portfolio_id=eq.{portfolio_id}&stock_symbol=eq.{stock_symbol}")
    if response.status_code != 200:
        return jsonify({"error": "Failed to fetch stock data", "details": response.json()}), response.status_code

    stock_data = response.json()
    if not stock_data:
        return jsonify({"error": "Stock not found in portfolio"}), 404

    return jsonify(stock_data[0])
