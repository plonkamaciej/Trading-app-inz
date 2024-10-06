from flask import Blueprint, request, jsonify
from supabase_client import get_from_supabase

get_portfolio_history_bp = Blueprint('get_portfolio_history', __name__)

@get_portfolio_history_bp.route('/get_portfolio_history', methods=['GET'])
def get_portfolio_history():
    portfolio_id = request.args.get('portfolio_id')

    # Validate portfolio_id
    if not portfolio_id:
        return jsonify({'error': 'Missing portfolio_id'}), 400

    # Prepare query parameters for Supabase
    params = {
        'portfolio_id': f'eq.{portfolio_id}',  # Filter based on portfolio_id
        'order': 'created_at.asc'  # Sort by created_at in ascending order
    }

    # Fetch historical data from portfolio_returns table
    response = get_from_supabase('portfolio_returns', params=params)

    # Ensure response is valid and can be converted to JSON
    if response.status_code != 200:
        return jsonify({'error': 'Failed to fetch portfolio history'}), response.status_code

    # Ensure the response can be parsed to JSON
    try:
        data = response.json()  # Parse the JSON data from the response
    except ValueError:
        return jsonify({'error': 'Invalid JSON response from Supabase'}), 500

    # Check if data is empty and return a 404 if no records are found
    if not data:
        return jsonify({'error': 'No portfolio history found for the given portfolio_id'}), 404

    # Return the parsed data
    return jsonify(data), 200
