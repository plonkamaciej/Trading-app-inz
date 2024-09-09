# routes/add_cash.py

from flask import Blueprint, request, jsonify
from supabase_client import patch_to_supabase, get_from_supabase
from config import TEST_PORTFOLIO_ID

add_cash_bp = Blueprint('add_cash', __name__)

@add_cash_bp.route('/add_cash', methods=['POST'])
def add_cash():
    data = request.json
    portfolio_id = data.get('portfolio_id', TEST_PORTFOLIO_ID)
    amount = data.get('amount')

    if not portfolio_id or amount is None:
        return jsonify({"error": "Missing required fields"}), 400

    # Fetch the current cash balance
    response = get_from_supabase(f"portfolios?portfolio_id=eq.{portfolio_id}")
    if response.status_code != 200:
        return jsonify({"error": "Failed to fetch portfolio data", "details": response.json()}), response.status_code

    portfolio_data = response.json()
    if not portfolio_data:
        return jsonify({"error": "Portfolio not found"}), 404

    current_cash_balance = portfolio_data[0].get('cash_balance', 0)
    new_cash_balance = current_cash_balance + amount

    # Update the cash balance
    response = patch_to_supabase(f"portfolios?portfolio_id=eq.{portfolio_id}", {"cash_balance": new_cash_balance})
    if response.status_code != 204:
        return jsonify({"error": "Failed to update cash balance", "details": response.json()}), response.status_code

    return jsonify({"message": "Cash added successfully", "new_cash_balance": new_cash_balance})
