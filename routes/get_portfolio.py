# routes/get_portfolio.py

from flask import Blueprint, request, jsonify
from supabase_client import get_from_supabase
from config import TEST_PORTFOLIO_ID

get_portfolio_bp = Blueprint('get_portfolio', __name__)

@get_portfolio_bp.route('/get_portfolio', methods=['GET'])
def get_portfolio():
    portfolio_id = request.args.get('portfolio_id', TEST_PORTFOLIO_ID)

    response = get_from_supabase(f"portfolios?portfolio_id=eq.{portfolio_id}")
    if response.status_code != 200:
        return jsonify({"error": "Failed to fetch portfolio data", "details": response.json()}), response.status_code

    portfolio_data = response.json()
    if not portfolio_data:
        return jsonify({"error": "Portfolio not found"}), 404

    return jsonify(portfolio_data[0])
