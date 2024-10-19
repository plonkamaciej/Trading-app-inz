import yfinance as yf
from supabase_client import get_from_supabase, patch_to_supabase, post_to_supabase
from datetime import datetime

def fetch_stock_prices(stock_symbols):
    try:
        tickers = yf.Tickers(' '.join(stock_symbols))
        stock_prices = {}
        for symbol in stock_symbols:
            ticker = tickers.tickers[symbol]
            stock_info = ticker.history(period="1d")
            current_price = stock_info['Close'].iloc[-1] if not stock_info.empty else None
            stock_prices[symbol] = current_price
        return stock_prices
    except Exception as e:
        print(f"Failed to fetch stock prices for {stock_symbols}: {str(e)}")
        return {}

def update_single_portfolio(portfolio_id):
    # Fetch the portfolio data
    portfolio_response = get_from_supabase(f"portfolios?portfolio_id=eq.{portfolio_id}")
    if portfolio_response.status_code != 200:
        print(f"Failed to fetch portfolio {portfolio_id}: {portfolio_response.text}")
        return None
    
    portfolio = portfolio_response.json()[0]
    cash_balance = portfolio.get('cash_balance', 0)
    user_id = portfolio.get('user_id')

    # Fetch the stocks for this portfolio
    stocks_response = get_from_supabase(f"portfolio_stocks?portfolio_id=eq.{portfolio_id}")
    if stocks_response.status_code != 200:
        print(f"Failed to fetch stocks for portfolio {portfolio_id}: {stocks_response.text}")
        return None
    
    stocks = stocks_response.json()

    total_stocks_value = 0.0
    stock_symbols = [stock['stock_symbol'] for stock in stocks if stock.get('quantity', 0) > 0]

    if stock_symbols:
        stock_prices = fetch_stock_prices(stock_symbols)
        for stock in stocks:
            stock_symbol = stock.get('stock_symbol')
            quantity = stock.get('quantity', 0)
            current_price = stock_prices.get(stock_symbol)

            if current_price and quantity > 0:
                total_stocks_value += quantity * current_price

    # Calculate total portfolio value (cash balance + total stocks value)
    total_portfolio_value = cash_balance + total_stocks_value

    # Update the portfolio value in the portfolios table
    patch_response = patch_to_supabase(f"portfolios?portfolio_id=eq.{portfolio_id}", {
        "total_value": total_portfolio_value
    })

    if patch_response.status_code == 200 or patch_response.status_code == 204:
        print(f"Successfully updated portfolio value for portfolio {portfolio_id}")
    else:
        print(f"Failed to update portfolio {portfolio_id}: {patch_response.text}")

    # Fetch transactions for this user
    transactions_response = get_from_supabase(f"transactions?user_id=eq.{user_id}")
    if transactions_response.status_code != 200:
        print(f"Failed to fetch transactions for user {user_id}: {transactions_response.text}")
        return None

    transactions = transactions_response.json()

    # Calculate invested value (total deposits - withdrawals)
    invested_value = sum(
        transaction['amount'] if transaction['transaction_type'] == 'DEPOSIT' else -transaction['amount']
        for transaction in transactions
        if transaction['transaction_type'] in ['DEPOSIT', 'WITHDRAWAL']
    )

    # Calculate return value (which is the total portfolio value in this case)
    return_value = total_portfolio_value

    # Get the current date and time
    current_datetime = datetime.utcnow().isoformat()

    # Update the portfolio_returns table
    return_data = {
        "portfolio_id": portfolio_id,
        "return_value": return_value,
        "invested_value": invested_value,
        "created_at": current_datetime
    }

    post_response = post_to_supabase("portfolio_returns", return_data)

    if post_response.status_code == 201:
        print(f"Successfully added portfolio return to portfolio_returns table for portfolio {portfolio_id}")
    else:
        print(f"Failed to add portfolio return to portfolio_returns table for portfolio {portfolio_id}: {post_response.text}")

    return total_portfolio_value
