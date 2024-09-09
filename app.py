from flask import Flask
from flask_cors import CORS
from config import HEADERS
from routes.buy_stock import buy_stock_bp
from routes.sell_stock import sell_stock_bp
from routes.get_portfolio import get_portfolio_bp
from routes.get_stock import get_stock_bp
from routes.get_all_stocks import get_all_stocks_bp
from routes.authenticate import authenticate_bp  # Ensure this import is correct
from routes.add_cash import add_cash_bp  # Ensure this import is correct

app = Flask(__name__)
CORS(app)

# Register blueprints
app.register_blueprint(buy_stock_bp)
app.register_blueprint(sell_stock_bp)
app.register_blueprint(get_portfolio_bp)
app.register_blueprint(get_stock_bp)
app.register_blueprint(get_all_stocks_bp)
app.register_blueprint(authenticate_bp)  # Register the new route
app.register_blueprint(add_cash_bp)  # Register the new route

if __name__ == '__main__':
    app.run(debug=True)
