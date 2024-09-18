from flask import Blueprint, request, jsonify
from supabase_client import get_from_supabase
import yfinance as yf

get_investment_chart_data_bp = Blueprint('get_investment_chart_data', __name__)

@get_investment_chart_data_bp.route('/get_investment_chart_data', methods=['GET'])
def get_investment_chart_data():
    user_id = request.args.get('user_id')

    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400

    # Fetch portfolio based on user_id
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

    # Fetch transaction history (deposits and withdrawals) using user_id
    transactions_response = get_from_supabase(f"transactions?user_id=eq.{user_id}")
    if transactions_response.status_code != 200:
        return jsonify({"error": "Failed to fetch transactions", "details": transactions_response.json()}), transactions_response.status_code

    transactions = transactions_response.json()

    # Accumulate deposits and withdrawals over time
    cumulative_investment = 0
    investment_data = []

    for transaction in transactions:
        transaction_type = transaction.get('transaction_type')
        amount = transaction.get('amount', 0)
        transaction_date = transaction.get('transaction_date')

        # Adjust based on transaction type
        if transaction_type == 'DEPOSIT':
            cumulative_investment += amount
        elif transaction_type == 'WITHDRAWAL':
            cumulative_investment -= amount

        # Append the data for charting
        investment_data.append({
            "date": transaction_date,
            "invested_amount": cumulative_investment
        })

    # Fetch stocks in the portfolio
    stocks_response = get_from_supabase(f"portfolio_stocks?portfolio_id=eq.{portfolio_id}")
    if stocks_response.status_code != 200:
        return jsonify({"error": "Failed to fetch stocks", "details": stocks_response.json()}), stocks_response.status_code

    stocks = stocks_response.json()
    total_stocks_value = 0.0

    # Fetch current prices for all stocks
    stock_symbols = [stock['stock_symbol'] for stock in stocks if stock.get('quantity', 0) > 0]
    if stock_symbols:
        tickers = yf.Tickers(' '.join(stock_symbols))
        for stock in stocks:
            stock_symbol = stock.get('stock_symbol')
            quantity = stock.get('quantity', 0)

            try:
                ticker = tickers.tickers[stock_symbol]
                stock_info = ticker.history(period="1d")
                current_price = stock_info['Close'].iloc[-1] if not stock_info.empty else None
                if current_price:
                    total_stocks_value += current_price * quantity
            except Exception as e:
                return jsonify({"error": f"Failed to fetch stock data for {stock_symbol}: {str(e)}"}), 500

    return jsonify({
        "user_id": user_id,
        "investment_over_time": investment_data,
    }), 200
