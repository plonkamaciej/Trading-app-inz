import yfinance as yf
from supabase_client import get_from_supabase, patch_to_supabase
import concurrent.futures

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

def update_portfolio(portfolio, stocks):
    portfolio_id = portfolio.get('portfolio_id')
    current_cash_balance = portfolio.get('cash_balance', 0)

    # Filter stocks belonging to the current portfolio
    portfolio_stocks = [stock for stock in stocks if stock['portfolio_id'] == portfolio_id]
    
    total_stocks_value = 0.0
    stock_symbols = [stock['stock_symbol'] for stock in portfolio_stocks if stock.get('quantity', 0) > 0]

    if stock_symbols:
        stock_prices = fetch_stock_prices(stock_symbols)
        for stock in portfolio_stocks:
            stock_symbol = stock.get('stock_symbol')
            quantity = stock.get('quantity', 0)
            current_price = stock_prices.get(stock_symbol)

            if current_price and quantity > 0:
                total_stocks_value += quantity * current_price

    # Calculate total portfolio value (cash balance + total stocks value)
    total_portfolio_value = current_cash_balance + total_stocks_value

    # Update the portfolio value in the portfolios table
    patch_response = patch_to_supabase(f"portfolios?portfolio_id=eq.{portfolio_id}", {
        "total_value": total_portfolio_value
    })

    if patch_response.status_code == 200 or patch_response.status_code == 204:
        print(f"Successfully updated portfolio value for portfolio {portfolio_id}")
    else:
        print(f"Failed to update portfolio {portfolio_id}: {patch_response.text}")

def update_all_portfolio_values():
    # Fetch all portfolios at once
    portfolio_response = get_from_supabase("portfolios")
    if portfolio_response.status_code != 200:
        print("Failed to fetch portfolios:", portfolio_response.text)
        return

    portfolios = portfolio_response.json()

    # Fetch all stocks at once
    stocks_response = get_from_supabase("portfolio_stocks")
    if stocks_response.status_code != 200:
        print("Failed to fetch stocks:", stocks_response.text)
        return
    
    stocks = stocks_response.json()

    # Use ThreadPoolExecutor to process portfolios concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(lambda portfolio: update_portfolio(portfolio, stocks), portfolios)

if __name__ == "__main__":
    update_all_portfolio_values()
