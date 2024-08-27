# app.py

from flask import Flask
from config import HEADERS
from routes.buy_stock import buy_stock_bp
from routes.sell_stock import sell_stock_bp
from routes.get_portfolio import get_portfolio_bp
from routes.get_stock import get_stock_bp
from routes.get_all_stocks import get_all_stocks_bp


app = Flask(__name__)

# Register blueprints
app.register_blueprint(buy_stock_bp)
app.register_blueprint(sell_stock_bp)
app.register_blueprint(get_portfolio_bp)
app.register_blueprint(get_stock_bp)
app.register_blueprint(get_all_stocks_bp)




if __name__ == '__main__':
    app.run(debug=True)
