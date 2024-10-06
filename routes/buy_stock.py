from flask import Blueprint, request, jsonify
from supabase_client import get_from_supabase, patch_to_supabase, post_to_supabase
import yfinance as yf
import logging

logger = logging.getLogger(__name__)

buy_stock_bp = Blueprint('buy_stock', __name__)

@buy_stock_bp.route('/buy_stock', methods=['POST'])
def buy_stock():
    logger.info("Rozpoczęto przetwarzanie żądania kupna akcji")
    
    if not request.is_json:
        logger.error("Otrzymane dane nie są w formacie JSON")
        return jsonify({"error": "Nieprawidłowy format danych, oczekiwano JSON"}), 400

    data = request.json
    logger.info(f"Otrzymane dane: {data}")

    required_fields = ['portfolio_id', 'stock_symbol', 'amount']
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        logger.error(f"Brakujące pola: {', '.join(missing_fields)}")
        return jsonify({"error": f"Brakujące wymagane pola: {', '.join(missing_fields)}"}), 400

    portfolio_id = data['portfolio_id']
    stock_symbol = data['stock_symbol']
    amount = data['amount']

    if not isinstance(portfolio_id, str):
        logger.error(f"Nieprawidłowy typ portfolio_id: {type(portfolio_id)}")
        return jsonify({"error": "portfolio_id musi być ciągiem znaków"}), 400

    if not isinstance(stock_symbol, str):
        logger.error(f"Nieprawidłowy typ stock_symbol: {type(stock_symbol)}")
        return jsonify({"error": "stock_symbol musi być ciągiem znaków"}), 400

    if not isinstance(amount, (int, float)):
        logger.error(f"Nieprawidłowy typ amount: {type(amount)}")
        return jsonify({"error": "amount musi być liczbą"}), 400

    logger.info(f"Przetwarzanie kupna: portfolio_id={portfolio_id}, stock_symbol={stock_symbol}, amount={amount}")

    try:
        stock = yf.Ticker(stock_symbol)
        stock_info = stock.history(period="1d")
        if stock_info.empty:
            return jsonify({"error": "Nie udało się pobrać ceny akcji"}), 400
        current_price = stock_info['Close'].iloc[0]
    except Exception as e:
        return jsonify({"error": f"Nie udało się pobrać ceny akcji: {str(e)}"}), 500

    quantity_to_buy = amount / current_price

    # Pobierz aktualny stan konta
    portfolio_response = get_from_supabase(f"portfolios?portfolio_id=eq.{portfolio_id}")
    if portfolio_response.status_code != 200:
        return jsonify({"error": "Nie udało się pobrać danych portfela"}), 500
    
    portfolio_data = portfolio_response.json()[0]
    current_cash_balance = portfolio_data.get('cash_balance', 0)

    if current_cash_balance < amount:
        return jsonify({"error": "Niewystarczające środki na koncie"}), 400

    new_cash_balance = current_cash_balance - amount

    # Aktualizuj stan konta
    response = patch_to_supabase(f"portfolios?portfolio_id=eq.{portfolio_id}", {"cash_balance": new_cash_balance})
    if response.status_code != 204:
        return jsonify({"error": "Nie udało się zaktualizować stanu konta", "details": response.json()}), response.status_code

    # Sprawdź, czy akcje już istnieją w portfelu
    stock_response = get_from_supabase(f"portfolio_stocks?portfolio_id=eq.{portfolio_id}&stock_symbol=eq.{stock_symbol}")
    stock_data = stock_response.json()

    if stock_data:
        # Aktualizuj istniejące akcje
        existing_stock = stock_data[0]
        new_quantity = existing_stock['quantity'] + quantity_to_buy
        new_total_investment = existing_stock['total_investment'] + amount
        new_average_price = new_total_investment / new_quantity

        response = patch_to_supabase(f"portfolio_stocks?portfolio_id=eq.{portfolio_id}&stock_symbol=eq.{stock_symbol}", {
            "quantity": new_quantity,
            "total_investment": new_total_investment,
            "average_price": new_average_price
        })
    else:
        # Dodaj nowe akcje do portfela
        response = post_to_supabase("portfolio_stocks", {
            "portfolio_id": portfolio_id,
            "stock_symbol": stock_symbol,
            "quantity": quantity_to_buy,
            "total_investment": amount,
            "average_price": current_price
        })

    if response.status_code not in [200, 201, 204]:
        return jsonify({"error": "Nie udało się zaktualizować stanu akcji", "details": response.json()}), response.status_code

    # Zaktualizuj całkowitą wartość portfela
    update_portfolio_total_value(portfolio_id)

    # Zarejestruj transakcję
    trade_response = post_to_supabase("trades", {
        "portfolio_id": portfolio_id,
        "stock_symbol": stock_symbol,
        "trade_type": "BUY",
        "quantity": quantity_to_buy,
        "price": current_price
    })
    if trade_response.status_code != 201:
        return jsonify({"error": "Nie udało się zarejestrować transakcji", "details": trade_response.json()}), trade_response.status_code

    return jsonify({
        "message": f"Kupiono akcje {stock_symbol} za ${amount:.2f}",
        "quantity_bought": quantity_to_buy,
        "new_cash_balance": new_cash_balance
    })

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