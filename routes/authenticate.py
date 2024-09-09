from flask import Blueprint, request, jsonify
import requests
from supabase_client import get_from_supabase, post_to_supabase
from config import SUPABASE_URL, HEADERS
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)

authenticate_bp = Blueprint('authenticate', __name__)

@authenticate_bp.route('/authenticate', methods=['POST'])
def authenticate():
    try:
        # Retrieve data from request
        data = request.json
        email = data.get('email')
        password = data.get('password')

        # Validate request data
        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400

        # Authenticate the user with Supabase
        auth_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
        auth_response = requests.post(auth_url, json={"email": email, "password": password}, headers=HEADERS)

        # Check if authentication was successful
        if auth_response.status_code != 200:
            logging.error("Authentication failed with status code %s", auth_response.status_code)
            return jsonify({"error": "Authentication failed", "details": auth_response.json()}), auth_response.status_code

        # Parse the user data from the authentication response
        user_data = auth_response.json()
        user_id = user_data.get('user', {}).get('id')

        if not user_id:
            logging.error("Failed to retrieve user ID from authentication response")
            return jsonify({"error": "Failed to retrieve user ID"}), 500

        logging.debug(f"Authenticated user ID: {user_id}")

        # Fetch the user's portfolio using Supabase client
        portfolio_response = get_from_supabase('portfolios', params={'user_id': f'eq.{user_id}'})

        # Check if portfolio fetch was successful
        if portfolio_response.status_code != 200:
            logging.error("Failed to fetch portfolio with status code %s", portfolio_response.status_code)
            return jsonify({"error": "Failed to fetch portfolio", "details": portfolio_response.json()}), portfolio_response.status_code

        portfolios = portfolio_response.json()

        # If no portfolio exists, create a new one
        if not portfolios:
            logging.debug("No portfolio found, creating a new one.")

            # Create a new portfolio for the user
            new_portfolio_response = post_to_supabase('portfolios', data={
                'user_id': user_id,
                'total_value': 10000.00  # Set an initial value for the portfolio
            })

            # Check if portfolio creation was successful
            if new_portfolio_response.status_code != 201:
                logging.error("Failed to create portfolio with status code %s", new_portfolio_response.status_code)
                return jsonify({"error": "Failed to create portfolio", "details": new_portfolio_response.json()}), new_portfolio_response.status_code

            # Parse the new portfolio ID from the response
            portfolio_id = new_portfolio_response.json().get('portfolio_id')
            if not portfolio_id:
                logging.error("Portfolio creation response did not contain a portfolio_id.")
                return jsonify({"error": "Portfolio creation did not return a portfolio_id"}), 500

            logging.debug(f"Created new portfolio with ID: {portfolio_id}")
        else:
            # Retrieve the existing portfolio ID from the portfolio list
            portfolio_id = portfolios[0].get('portfolio_id')
            logging.debug(f"Existing portfolio ID: {portfolio_id}")

        # Return the user and portfolio information in the response
        return jsonify({
            "user_id": user_id,
            "portfolio_id": portfolio_id,
            "email": user_data.get('user', {}).get('email')
        })

    except requests.exceptions.RequestException as e:
        logging.error(f"RequestException occurred: {e}")
        return jsonify({"error": "An error occurred during the authentication process"}), 500
    except Exception as e:
        logging.error(f"Unexpected error occurred: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500
