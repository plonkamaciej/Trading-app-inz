from flask import Blueprint, request, jsonify
from supabase_client import patch_to_supabase, get_from_supabase, post_to_supabase
from config import TEST_PORTFOLIO_ID
from datetime import datetime

add_cash_bp = Blueprint('add_cash', __name__)

@add_cash_bp.route('/add_cash', methods=['POST'])
def add_cash():
    data = request.json
    portfolio_id = data.get('portfolio_id', TEST_PORTFOLIO_ID)
    user_id = data.get('user_id')  # Assuming user_id is passed in the request
    amount = data.get('amount')

    if not portfolio_id or amount is None or not user_id:
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

    # Update the cash balance in the portfolio
    response = patch_to_supabase(f"portfolios?portfolio_id=eq.{portfolio_id}", {"cash_balance": new_cash_balance})
    if response.status_code != 204:
        return jsonify({"error": "Failed to update cash balance", "details": response.json()}), response.status_code

    # Write the deposit transaction to the transactions table using POST
    transaction_data = {
    "user_id": user_id,
    "transaction_type": "DEPOSIT",  # Use the correct uppercase value
    "amount": amount,
    "transaction_date": datetime.utcnow().isoformat()  # Ensure the date is in UTC format
}

    transaction_response = post_to_supabase("transactions", transaction_data)

    # Check if the transaction was successfully inserted
    if transaction_response.status_code != 201:
        print(f"Transaction Insert Failed: {transaction_response.json()}")
        return jsonify({"error": "Failed to log deposit transaction", "details": transaction_response.json()}), transaction_response.status_code

    return jsonify({
        "message": "Cash added successfully",
        "new_cash_balance": new_cash_balance,
        "transaction_id": transaction_response.json().get('transaction_id')
    })
