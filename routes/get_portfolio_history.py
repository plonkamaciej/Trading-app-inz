from flask import Blueprint, request, jsonify
from supabase_client import get_from_supabase

get_portfolio_history_bp = Blueprint('get_portfolio_history', __name__)

@get_portfolio_history_bp.route('/get_portfolio_history', methods=['GET'])
def get_portfolio_history():
    portfolio_id = request.args.get('portfolio_id')

    # Validate portfolio_id
    if not portfolio_id:
        return jsonify({'error': 'Missing portfolio_id'}), 400

    # Prepare the parameters for the request
    params = {
        'portfolio_id': f'eq.{portfolio_id}',
        'order': 'recorded_at.asc'
    }

    # Fetch historical data from portfolio_history table
    response = get_from_supabase('portfolio_history', params=params)

    if response.status_code != 200:
        return jsonify({'error': 'Failed to fetch portfolio history'}), response.status_code

    return jsonify(response.json())
