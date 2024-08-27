# routes/sell_stock.py

from flask import Blueprint, request, jsonify
from supabase_client import get_from_supabase, post_to_supabase, patch_to_supabase, delete_from_supabase
from config import TEST_PORTFOLIO_ID

sell_stock_bp = Blueprint('sell_stock', __name__)

@sell_stock_bp.route('/sell_stock', methods=['POST'])
def sell_stock():
    data = request.json
    portfolio_id = data.get('portfolio_id', TEST_PORTFOLIO_ID)
    stock_symbol = data.get('stock_symbol')
    quantity = data.get('quantity')
    selling_price = data.get('selling_price')

    if not portfolio_id or not stock_symbol or not quantity or not selling_price:
        return jsonify({"error": "Missing required fields"}), 400

    # Check if stock is in the portfolio
    response = get_from_supabase(f"portfolio_stocks?portfolio_id=eq.{portfolio_id}&stock_symbol=eq.{stock_symbol}")
    if response.status_code != 200:
        return jsonify({"error": "Failed to fetch stock data", "details": response.json()}), response.status_code

    stock_data = response.json()

    if not stock_data:
        return jsonify({"error": "Stock not found in portfolio"}), 404

    existing_quantity = stock_data[0].get('quantity')
    existing_avg_price = stock_data[0].get('average_price')

    if existing_quantity < quantity:
        return jsonify({"error": "Not enough stock to sell"}), 400

    # Calculate new average price and quantity
    new_quantity = existing_quantity - quantity
    new_avg_price = existing_avg_price if new_quantity > 0 else None

    # Record the sale
    trade_response = post_to_supabase(
        "trades",
        {"portfolio_id": portfolio_id, "stock_symbol": stock_symbol, "trade_type": "SELL", "quantity": quantity, "price": selling_price}
    )
    if trade_response.status_code != 201:
        return jsonify({"error": "Failed to record trade", "details": trade_response.json()}), trade_response.status_code

    # Update Portfolio_Stocks
    if new_quantity > 0:
        response = patch_to_supabase(
            f"portfolio_stocks?portfolio_id=eq.{portfolio_id}&stock_symbol=eq.{stock_symbol}",
            {"quantity": new_quantity, "average_price": new_avg_price}
        )
        if response.status_code != 204:
            return jsonify({"error": "Failed to update stock data", "details": response.json()}), response.status_code
    else:
        response = delete_from_supabase(
            f"portfolio_stocks?portfolio_id=eq.{portfolio_id}&stock_symbol=eq.{stock_symbol}"
        )
        if response.status_code != 204:
            return jsonify({"error": "Failed to remove stock from portfolio", "details": response.json()}), response.status_code

    # Update Portfolio Total Value
    response = get_from_supabase(f"portfolios?portfolio_id=eq.{portfolio_id}")
    if response.status_code != 200:
        return jsonify({"error": "Failed to fetch portfolio data", "details": response.json()}), response.status_code

    portfolio_data = response.json()
    if not portfolio_data:
        return jsonify({"error": "Portfolio not found"}), 404

    current_total_value = portfolio_data[0].get('total_value', 0)
    profit_or_loss = (selling_price - existing_avg_price) * quantity
    new_total_value = current_total_value + profit_or_loss

    response = patch_to_supabase(
        f"portfolios?portfolio_id=eq.{portfolio_id}",
        {"total_value": new_total_value, "cash_balance": current_total_value + profit_or_loss}
    )
    if response.status_code != 204:
        return jsonify({"error": "Failed to update portfolio value and cash balance", "details": response.json()}), response.status_code

    return jsonify({"message": "Stock sold and portfolio updated"})
