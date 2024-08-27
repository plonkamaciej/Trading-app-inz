# routes/buy_stock.py

from flask import Blueprint, request, jsonify
from supabase_client import get_from_supabase, post_to_supabase, patch_to_supabase
from config import TEST_PORTFOLIO_ID

buy_stock_bp = Blueprint('buy_stock', __name__)

@buy_stock_bp.route('/buy_stock', methods=['POST'])
def buy_stock():
    data = request.json
    portfolio_id = data.get('portfolio_id', TEST_PORTFOLIO_ID)
    stock_symbol = data.get('stock_symbol')
    quantity = data.get('quantity')
    buying_price = data.get('buying_price')

    if not portfolio_id or not stock_symbol or not quantity or not buying_price:
        return jsonify({"error": "Missing required fields"}), 400

    # Check cash balance
    response = get_from_supabase(f"portfolios?portfolio_id=eq.{portfolio_id}")
    if response.status_code != 200:
        return jsonify({"error": "Failed to fetch portfolio data", "details": response.json()}), response.status_code

    portfolio_data = response.json()
    if not portfolio_data:
        return jsonify({"error": "Portfolio not found"}), 404

    cash_balance = portfolio_data[0].get('cash_balance', 0)
    total_cost = buying_price * quantity

    if cash_balance < total_cost:
        return jsonify({"error": "Insufficient cash balance"}), 400

    # Deduct the cost from cash balance
    new_cash_balance = cash_balance - total_cost
    response = patch_to_supabase(f"portfolios?portfolio_id=eq.{portfolio_id}", {"cash_balance": new_cash_balance})
    if response.status_code != 204:
        return jsonify({"error": "Failed to update cash balance", "details": response.json()}), response.status_code

    # Proceed with buying stock
    response = get_from_supabase(f"portfolio_stocks?portfolio_id=eq.{portfolio_id}&stock_symbol=eq.{stock_symbol}")
    if response.status_code != 200:
        return jsonify({"error": "Failed to fetch stock data", "details": response.json()}), response.status_code

    stock_data = response.json()

    if stock_data:
        # Update existing stock entry
        existing_quantity = stock_data[0].get('quantity')
        existing_avg_price = stock_data[0].get('average_price')
        new_quantity = existing_quantity + quantity
        new_avg_price = ((existing_avg_price * existing_quantity) + (buying_price * quantity)) / new_quantity

        response = patch_to_supabase(
            f"portfolio_stocks?portfolio_id=eq.{portfolio_id}&stock_symbol=eq.{stock_symbol}",
            {"quantity": new_quantity, "average_price": new_avg_price}
        )
        if response.status_code != 204:
            return jsonify({"error": "Failed to update stock data", "details": response.json()}), response.status_code
    else:
        # Insert new stock entry
        response = post_to_supabase(
            "portfolio_stocks",
            {"portfolio_id": portfolio_id, "stock_symbol": stock_symbol, "quantity": quantity, "average_price": buying_price}
        )
        if response.status_code != 201:
            return jsonify({"error": "Failed to add stock to portfolio", "details": response.json()}), response.status_code

    # Record the trade
    trade_response = post_to_supabase(
        "trades",
        {"portfolio_id": portfolio_id, "stock_symbol": stock_symbol, "trade_type": "BUY", "quantity": quantity, "price": buying_price}
    )
    if trade_response.status_code != 201:
        return jsonify({"error": "Failed to record trade", "details": trade_response.json()}), trade_response.status_code

    return jsonify({"message": "Stock bought successfully and trade recorded"})
