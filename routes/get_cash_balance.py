# routes/get_cash_balance.py

from flask import Blueprint, request, jsonify
from supabase_client import get_from_supabase
import yfinance as yf

get_cash_balance_bp = Blueprint('get_cash_balance', __name__)

@get_cash_balance_bp.route('/get_cash_balance', methods=['GET'])
def get_cash_balance():
    user_id = request.args.get('user_id')

    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400

    # Fetch the portfolio data
    portfolio_response = get_from_supabase(f"portfolios?user_id=eq.{user_id}")
    if portfolio_response.status_code != 200:
        return jsonify({
            "error": "Failed to fetch portfolio data",
            "details": portfolio_response.json()
        }), portfolio_response.status_code

    portfolio_data = portfolio_response.json()
    if not portfolio_data:
        return jsonify({"error": "Portfolio not found"}), 404

    portfolio_id = portfolio_data[0].get('portfolio_id')
    current_cash_balance = portfolio_data[0].get('cash_balance', 0)

    # Fetch transaction history (deposits and withdrawals) by user_id
    transactions_response = get_from_supabase(f"transactions?user_id=eq.{user_id}")
    if transactions_response.status_code != 200:
        return jsonify({"error": "Failed to fetch transactions", "details": transactions_response.json()}), transactions_response.status_code

    transactions = transactions_response.json()

    total_deposits = sum(
        transaction['amount'] for transaction in transactions if transaction['transaction_type'] == 'DEPOSIT'
    )
    total_withdrawals = sum(
        transaction['amount'] for transaction in transactions if transaction['transaction_type'] == 'WITHDRAWAL'
    )

    total_invested = total_deposits - total_withdrawals

    # Fetch stocks and calculate current value
    stocks_response = get_from_supabase(f"portfolio_stocks?portfolio_id=eq.{portfolio_id}")
    if stocks_response.status_code != 200:
        return jsonify({"error": "Failed to fetch stocks", "details": stocks_response.json()}), stocks_response.status_code

    stocks = stocks_response.json()
    total_stocks_value = 0.0
    stock_symbols = [stock['stock_symbol'] for stock in stocks if stock.get('quantity', 0) > 0]

    if stock_symbols:
        tickers = yf.Tickers(' '.join(stock_symbols))
        for stock in stocks:
            stock_symbol = stock.get('stock_symbol')
            quantity = stock.get('quantity', 0)

            if quantity <= 0:
                continue

            try:
                ticker = tickers.tickers[stock_symbol]
                stock_info = ticker.history(period="1d")
                current_price = stock_info['Close'].iloc[-1] if not stock_info.empty else None
            except Exception as e:
                return jsonify({"error": f"Failed to fetch data for {stock_symbol}: {str(e)}"}), 500

            if current_price:
                total_stocks_value += quantity * current_price

    total_portfolio_value = current_cash_balance + total_stocks_value

    return jsonify({
        "user_id": user_id,
        "cash_balance": current_cash_balance,
        "total_stocks_value": total_stocks_value,
        "total_portfolio_value": total_portfolio_value,
        "total_invested": total_invested
    }), 200
