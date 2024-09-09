from flask import Blueprint, request, jsonify
from supabase_client import get_from_supabase, post_to_supabase, patch_to_supabase
from config import TEST_PORTFOLIO_ID
import yfinance as yf
import logging

buy_stock_bp = Blueprint('buy_stock', __name__)

@buy_stock_bp.route('/buy_stock', methods=['POST'])
def buy_stock():
    data = request.json
    portfolio_id = data.get('portfolio_id', TEST_PORTFOLIO_ID)
    stock_symbol = data.get('stock_symbol')
    quantity = data.get('quantity')

    if not portfolio_id or not stock_symbol or not quantity:
        return jsonify({"error": "Missing required fields"}), 400

    if quantity <= 0:
        return jsonify({"error": "Quantity must be greater than 0"}), 400

    try:
        stock = yf.Ticker(stock_symbol)
        stock_info = stock.history(period="1d")
        if stock_info.empty:
            return jsonify({"error": "Failed to fetch stock price"}), 400
        current_price = stock_info['Close'].iloc[0]
    except Exception as e:
        logging.error(f"Failed to fetch stock price: {e}")
        return jsonify({"error": f"Failed to fetch stock price: {str(e)}"}), 500

    # Fetch portfolio data
    portfolio_response = get_from_supabase(f"portfolios?portfolio_id=eq.{portfolio_id}")
    if portfolio_response.status_code != 200:
        return jsonify({"error": "Failed to fetch portfolio data"}), portfolio_response.status_code

    portfolio_data = portfolio_response.json()[0]
    cash_balance = portfolio_data.get('cash_balance', 0)
    total_cost = current_price * quantity

    if cash_balance < total_cost:
        return jsonify({"error": "Insufficient cash balance"}), 400

    # Deduct the cost from the cash balance
    new_cash_balance = cash_balance - total_cost
    patch_to_supabase(f"portfolios?portfolio_id=eq.{portfolio_id}", {"cash_balance": new_cash_balance})

    # Check if the stock already exists in portfolio_stocks
    stock_response = get_from_supabase(f"portfolio_stocks?portfolio_id=eq.{portfolio_id}&stock_symbol=eq.{stock_symbol}")
    stock_data = stock_response.json()

    if stock_data:
        # Update the stock entry if it already exists
        stock_entry = stock_data[0]
        existing_quantity = stock_entry.get('quantity', 0)
        existing_avg_price = stock_entry.get('average_price', 0)

        new_quantity = existing_quantity + quantity
        new_avg_price = ((existing_avg_price * existing_quantity) + (current_price * quantity)) / new_quantity

        response = patch_to_supabase(f"portfolio_stocks?portfolio_id=eq.{portfolio_id}&stock_symbol=eq.{stock_symbol}", {
            "quantity": new_quantity,
            "average_price": new_avg_price,
            # Do not manually update total_investment if it's a generated column
        })

        if response.status_code != 204:
            logging.error(f"Failed to update stock: {response.json()}")
            return jsonify({"error": "Failed to update stock", "details": response.json()}), response.status_code

    else:
        # Insert a new stock entry if it doesn't exist
        response = post_to_supabase("portfolio_stocks", {
            "portfolio_id": portfolio_id,
            "stock_symbol": stock_symbol,
            "quantity": quantity,
            "average_price": current_price,
            # Do not manually insert total_investment if it's a generated column
        })

        if response.status_code != 201:
            logging.error(f"Failed to insert new stock: {response.json()}")
            return jsonify({"error": "Failed to insert new stock", "details": response.json()}), response.status_code

    # Update portfolio's total value
    update_portfolio_total_value(portfolio_id)

    # Record the trade
    trade_response = post_to_supabase("trades", {
        "portfolio_id": portfolio_id,
        "stock_symbol": stock_symbol,
        "trade_type": "BUY",
        "quantity": quantity,
        "price": current_price
    })

    if trade_response.status_code != 201:
        logging.error(f"Failed to record trade: {trade_response.json()}")
        return jsonify({"error": "Failed to record trade", "details": trade_response.json()}), trade_response.status_code

    return jsonify({"message": "Stock bought successfully at ${:.2f} per share.".format(current_price)})


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

    # Fetch all stocks in the portfolio
    stock_response = get_from_supabase(f"portfolio_stocks?portfolio_id=eq.{portfolio_id}")
    stocks = stock_response.json()

    # Calculate the total stock value based on the total_investment field
    # Ensure that 'None' values are replaced with 0
    total_stock_value = sum(stock.get('total_investment', 0) or 0 for stock in stocks)

    # The total value of the portfolio is the cash balance + total stock investments
    total_value = cash_balance + total_stock_value

    # Update the portfolio with the new total value
    patch_to_supabase(f"portfolios?portfolio_id=eq.{portfolio_id}", {"total_value": total_value})

    logging.debug(f"Updated portfolio {portfolio_id} total value to {total_value}")
