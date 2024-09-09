from flask import Blueprint, request, jsonify
import yfinance as yf
from supabase_client import get_from_supabase

get_all_stocks_bp = Blueprint('get_all_stocks', __name__)

@get_all_stocks_bp.route('/get_all_stocks', methods=['GET'])
def get_all_stocks():
    user_id = request.args.get('user_id')

    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400

    # Fetch portfolio associated with the user
    portfolio_response = get_from_supabase('portfolios', params={'user_id': f'eq.{user_id}'})
    if portfolio_response.status_code != 200:
        return jsonify({"error": "Failed to fetch portfolio", "details": portfolio_response.json()}), portfolio_response.status_code

    portfolios = portfolio_response.json()

    if not portfolios:
        return jsonify({"error": "No portfolio found for user"}), 404

    portfolio_id = portfolios[0].get('portfolio_id')

    # Fetch all stocks in the portfolio
    stocks_response = get_from_supabase('portfolio_stocks', params={'portfolio_id': f'eq.{portfolio_id}'})
    if stocks_response.status_code != 200:
        return jsonify({"error": "Failed to fetch stocks", "details": stocks_response.json()}), stocks_response.status_code

    stocks = stocks_response.json()

    if not stocks:
        return jsonify({"error": "No stocks found in portfolio"}), 404

    owned_stocks = []

    for stock in stocks:
        stock_symbol = stock.get('stock_symbol')
        quantity = stock.get('quantity')
        average_price = stock.get('average_price')

        # Fetch current price and company name using yfinance
        try:
            ticker = yf.Ticker(stock_symbol)
            stock_info = ticker.history(period="1d")
            current_price = stock_info['Close'].iloc[0] if not stock_info.empty else None
            company_name = ticker.info['shortName'] if 'shortName' in ticker.info else stock_symbol  # Get company name
        except Exception as e:
            return jsonify({"error": f"Failed to fetch data for {stock_symbol}: {str(e)}"}), 500

        # Calculate current value and return
        current_value = quantity * current_price if current_price else 0
        percentage_return = ((current_price - average_price) / average_price * 100) if current_price else 0

        owned_stocks.append({
            "stock_symbol": stock_symbol,
            "quantity": quantity,
            "average_price": average_price,
            "current_price": current_price,
            "value": current_value,
            "return": f"{percentage_return:.2f}%",  # Return as percentage
            "company_name": company_name  # Add company name to response
        })

    return jsonify({"owned_stocks": owned_stocks})
