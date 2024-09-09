from flask import Blueprint, request, jsonify
from supabase_client import get_from_supabase, patch_to_supabase, post_to_supabase
from config import TEST_PORTFOLIO_ID
import yfinance as yf
import logging

sell_stock_bp = Blueprint('sell_stock', __name__)

@sell_stock_bp.route('/sell_stock', methods=['POST'])
def sell_stock():
    data = request.json
    portfolio_id = data.get('portfolio_id', TEST_PORTFOLIO_ID)
    stock_symbol = data.get('stock_symbol')
    quantity = data.get('quantity')

    if not portfolio_id or not stock_symbol or not quantity:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        # Fetch the current stock price from yfinance
        stock = yf.Ticker(stock_symbol)
        stock_info = stock.history(period="1d")
        if stock_info.empty:
            return jsonify({"error": "Failed to fetch stock price"}), 400
        current_price = stock_info['Close'].iloc[0]
    except Exception as e:
        return jsonify({"error": f"Failed to fetch stock price: {str(e)}"}), 500

    # Fetch the stock information from the portfolio
    stock_response = get_from_supabase(f"portfolio_stocks?portfolio_id=eq.{portfolio_id}&stock_symbol=eq.{stock_symbol}")
    stock_data = stock_response.json()

    if not stock_data or stock_data[0].get('quantity', 0) < quantity:
        return jsonify({"error": "Not enough stock quantity to sell"}), 400

    stock_entry = stock_data[0]
    remaining_quantity = stock_entry.get('quantity') - quantity

    # Soft delete: If remaining quantity is greater than 0, update it. If 0, just set the quantity to 0.
    if remaining_quantity > 0:
        new_total_investment = remaining_quantity * stock_entry['average_price']
        response = patch_to_supabase(f"portfolio_stocks?portfolio_id=eq.{portfolio_id}&stock_symbol=eq.{stock_symbol}", {
            "quantity": remaining_quantity,
            "total_investment": new_total_investment
        })
        if response.status_code != 204:
            return jsonify({"error": "Failed to update stock data", "details": response.json()}), response.status_code
    else:
        # Set the quantity to 0 (soft delete)
        response = patch_to_supabase(f"portfolio_stocks?portfolio_id=eq.{portfolio_id}&stock_symbol=eq.{stock_symbol}", {
            "quantity": 0
        })
        if response.status_code != 204:
            return jsonify({"error": "Failed to set stock quantity to 0", "details": response.json()}), response.status_code

    # Add the sale amount to the portfolio's cash balance
    sale_amount = current_price * quantity
    portfolio_response = get_from_supabase(f"portfolios?portfolio_id=eq.{portfolio_id}")
    portfolio_data = portfolio_response.json()[0]
    new_cash_balance = portfolio_data.get('cash_balance', 0) + sale_amount

    response = patch_to_supabase(f"portfolios?portfolio_id=eq.{portfolio_id}", {"cash_balance": new_cash_balance})
    if response.status_code != 204:
        return jsonify({"error": "Failed to update cash balance", "details": response.json()}), response.status_code

    # Update the portfolio's total value
    update_portfolio_total_value(portfolio_id)

    # Record the trade
    trade_response = post_to_supabase("trades", {
        "portfolio_id": portfolio_id,
        "stock_symbol": stock_symbol,
        "trade_type": "SELL",
        "quantity": quantity,
        "price": current_price
    })
    if trade_response.status_code != 201:
        return jsonify({"error": "Failed to record trade", "details": trade_response.json()}), trade_response.status_code

    return jsonify({"message": "Stock sold successfully and trade recorded", "new_cash_balance": new_cash_balance})

def update_portfolio_total_value(portfolio_id):
    """
    Recalculate and update the portfolio's total value (cash balance + total stock investments).
    """
    # Fetch the portfolio data
    portfolio_response = get_from_supabase(f"portfolios?portfolio_id=eq.{portfolio_id}")
    if portfolio_response.status_code != 200:
        logging.error(f"Failed to fetch portfolio data for total value update.")
        return

    portfolio_data = portfolio_response.json()[0]
    cash_balance = portfolio_data.get('cash_balance', 0)

    # Fetch the total investment in stocks
    stock_response = get_from_supabase(f"portfolio_stocks?portfolio_id=eq.{portfolio_id}")
    stocks = stock_response.json()

    # Calculate total stock value, handling NoneType
    total_stock_value = sum(stock.get('total_investment', 0) or 0 for stock in stocks if stock.get('quantity', 0) > 0)

    # Calculate the total value (cash balance + total stock investments)
    total_value = cash_balance + total_stock_value

    # Update the portfolio with the new total value
    patch_response = patch_to_supabase(f"portfolios?portfolio_id=eq.{portfolio_id}", {"total_value": total_value})
    if patch_response.status_code != 204:
        logging.error(f"Failed to update portfolio total value.")
