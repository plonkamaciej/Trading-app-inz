from flask import Blueprint, request, jsonify
from supabase_client import get_from_supabase, post_to_supabase, delete_from_supabase
import yfinance as yf
from datetime import datetime, timedelta

watchlist_bp = Blueprint('watchlist', __name__)

def get_stock_data(symbol):
    """
    Funkcja pobierająca rozszerzone dane o akcjach za pomocą yfinance.
    """
    try:
        ticker = yf.Ticker(symbol)
        stock_info = ticker.info
        
        # Pobierz dane za ostatnie 2 dni
        end_date = datetime.now()
        start_date = end_date - timedelta(days=2)
        history = ticker.history(start=start_date, end=end_date)
        
        if history.empty:
            print(f"Brak danych historycznych dla {symbol}")
            return None

        current_price = history['Close'].iloc[-1]
        previous_close = history['Close'].iloc[-2] if len(history) > 1 else current_price
        daily_return = ((current_price - previous_close) / previous_close) * 100

        return {
            'stock_symbol': symbol,
            'company_name': stock_info.get('shortName', symbol),
            'current_price': current_price,
            'daily_return': round(daily_return, 2),
            'day_low': history['Low'].iloc[-1],
            'day_high': history['High'].iloc[-1],
            'fifty_two_week_low': stock_info.get('fiftyTwoWeekLow'),
            'fifty_two_week_high': stock_info.get('fiftyTwoWeekHigh')
        }
    except Exception as e:
        print(f"Błąd podczas pobierania danych dla {symbol}: {str(e)}")
        return None

@watchlist_bp.route('/watchlist', methods=['GET'])
def get_user_watchlist():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "Brak ID użytkownika"}), 400

    print(f"Pobieranie watchlisty dla użytkownika: {user_id}")

    watchlist_response = get_from_supabase('watchlists', {'user_id': f'eq.{user_id}'})
    if watchlist_response.status_code != 200:
        print(f"Błąd podczas pobierania watchlisty: {watchlist_response.status_code}, {watchlist_response.text}")
        return jsonify({"error": "Nie udało się pobrać watchlisty"}), 500

    watchlists = watchlist_response.json()
    print(f"Pobrane watchlisty: {watchlists}")

    if not watchlists:
        print("Użytkownik nie ma jeszcze watchlisty")
        return jsonify([]), 200

    watchlist_id = watchlists[0]['watchlist_id']
    print(f"ID watchlisty: {watchlist_id}")

    stocks_response = get_from_supabase('watchlist_stocks', {'watchlist_id': f'eq.{watchlist_id}'})
    if stocks_response.status_code != 200:
        print(f"Błąd podczas pobierania akcji z watchlisty: {stocks_response.status_code}, {stocks_response.text}")
        return jsonify({"error": "Nie udało się pobrać akcji z watchlisty"}), 500

    watchlist_stocks = stocks_response.json()
    print(f"Pobrane akcje z watchlisty: {watchlist_stocks}")
    
    updated_stocks = []
    for stock in watchlist_stocks:
        stock_data = get_stock_data(stock['stock_symbol'])
        if stock_data:
            updated_stocks.append(stock_data)
        else:
            print(f"Nie udało się pobrać danych dla {stock['stock_symbol']}")

    print(f"Zaktualizowane dane akcji: {updated_stocks}")
    return jsonify(updated_stocks), 200

@watchlist_bp.route('/watchlist/add', methods=['POST'])
def add_to_watchlist():
    data = request.json
    user_id = data.get('user_id')
    stock_symbol = data.get('stock_symbol')

    if not user_id or not stock_symbol:
        return jsonify({"error": "Brak wymaganych danych"}), 400

    print(f"Dodawanie akcji {stock_symbol} do watchlisty użytkownika {user_id}")

    # Sprawdź, czy symbol akcji jest prawidłowy
    stock_data = get_stock_data(stock_symbol)
    if not stock_data:
        return jsonify({"error": f"Nie udało się pobrać danych dla akcji {stock_symbol}"}), 400

    # Pobierz lub utwórz watchlistę dla użytkownika
    watchlist_response = get_from_supabase('watchlists', {'user_id': f'eq.{user_id}'})
    if watchlist_response.status_code != 200:
        print(f"Błąd podczas pobierania watchlisty: {watchlist_response.status_code}, {watchlist_response.text}")
        return jsonify({"error": "Nie udało się pobrać watchlisty"}), 500

    watchlists = watchlist_response.json()
    if not watchlists:
        print("Tworzenie nowej watchlisty dla użytkownika")
        new_watchlist = {'user_id': user_id, 'watchlist_name': 'Default Watchlist'}
        watchlist_create_response = post_to_supabase('watchlists', new_watchlist)
        if watchlist_create_response.status_code != 201:
            print(f"Błąd podczas tworzenia watchlisty: {watchlist_create_response.status_code}, {watchlist_create_response.text}")
            return jsonify({"error": "Nie udało się utworzyć watchlisty"}), 500
        watchlist_id = watchlist_create_response.json()[0]['watchlist_id']
    else:
        watchlist_id = watchlists[0]['watchlist_id']

    print(f"ID watchlisty: {watchlist_id}")

    # Sprawdź, czy akcja już istnieje w liście obserwowanych
    existing = get_from_supabase('watchlist_stocks', {
        'watchlist_id': f'eq.{watchlist_id}',
        'stock_symbol': f'eq.{stock_symbol}'
    })
    
    if existing.json():
        return jsonify({"message": "Akcja już jest na liście obserwowanych"}), 200

    # Dodaj akcję do listy obserwowanych
    new_stock = {
        'watchlist_id': watchlist_id,
        'stock_symbol': stock_symbol
    }
    response = post_to_supabase('watchlist_stocks', new_stock)
    
    if response.status_code != 201:
        print(f"Błąd podczas dodawania do watchlisty: {response.status_code}, {response.text}")
        return jsonify({"error": "Nie udało się dodać akcji do listy obserwowanych"}), 500

    print(f"Akcja {stock_symbol} dodana do watchlisty")
    return jsonify({"message": "Akcja dodana do listy obserwowanych"}), 201

@watchlist_bp.route('/watchlist/remove', methods=['DELETE'])
def remove_from_watchlist():
    user_id = request.args.get('user_id')
    stock_symbol = request.args.get('stock_symbol')

    if not user_id or not stock_symbol:
        return jsonify({"error": "Brak wymaganych danych"}), 400

    # Pobierz watchlist_id dla użytkownika
    watchlist_response = get_from_supabase('watchlists', {'user_id': f'eq.{user_id}'})
    if watchlist_response.status_code != 200 or not watchlist_response.json():
        return jsonify({"error": "Nie znaleziono watchlisty dla użytkownika"}), 404

    watchlist_id = watchlist_response.json()[0]['watchlist_id']

    # Usuń akcję z listy obserwowanych
    response = delete_from_supabase('watchlist_stocks', {
        'watchlist_id': f'eq.{watchlist_id}',
        'stock_symbol': f'eq.{stock_symbol}'
    })

    if response.status_code == 204:
        return jsonify({"message": "Akcja usunięta z listy obserwowanych"}), 200
    elif response.status_code == 404:
        return jsonify({"error": "Nie znaleziono akcji na liście obserwowanych"}), 404
    else:
        print(f"Błąd podczas usuwania akcji: {response.status_code}, {response.text}")
        return jsonify({"error": "Nie udało się usunąć akcji z listy obserwowanych"}), 500

# Pamiętaj, aby zarejestrować ten blueprint w głównej aplikacji Flask