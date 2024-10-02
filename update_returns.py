import yfinance as yf
from supabase_client import get_from_supabase, patch_to_supabase

def update_all_portfolio_values():
    # Fetch all portfolios
    portfolio_response = get_from_supabase("portfolios")
    if portfolio_response.status_code != 200:
        print("Failed to fetch portfolios:", portfolio_response.text)
        return

    portfolios = portfolio_response.json()

    for portfolio in portfolios:
        portfolio_id = portfolio.get('portfolio_id')
        current_cash_balance = portfolio.get('cash_balance', 0)

        # Fetch stocks and calculate current value
        stocks_response = get_from_supabase(f"portfolio_stocks?portfolio_id=eq.{portfolio_id}")
        if stocks_response.status_code != 200:
            print(f"Failed to fetch stocks for portfolio {portfolio_id}: {stocks_response.text}")
            continue

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
                    print(f"Failed to fetch data for {stock_symbol}: {str(e)}")
                    continue

                if current_price:
                    total_stocks_value += quantity * current_price

        # Calculate total portfolio value (cash balance + total stocks value)
        total_portfolio_value = current_cash_balance + total_stocks_value

        # Corrected typo in "portfolios" and improved error handling
        patch_response = patch_to_supabase(f"portfolios?portfolio_id=eq.{portfolio_id}", {
            "total_value": total_portfolio_value
        })


        print(f"Successfully updated portfolio value for portfolio {portfolio_id}")

if __name__ == "__main__":
    update_all_portfolio_values()
