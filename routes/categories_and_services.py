
# route to get categories and services
from flask import Blueprint, jsonify

from database.get_categories_and_services.fetch_categories_and_services import fetch_categories_and_services

categories_and_services_bp = Blueprint('categories_and_services_bp', __name__)

@categories_and_services_bp.route('/get_categories_and_services', methods=['GET'])
def get_categories_and_services():
    try:
        # Call the database function to fetch categories and services
        categories_services = fetch_categories_and_services()

        # Check if there was an error during fetching
        if categories_services is None:
            return jsonify({"error": "An error occurred while fetching categories and services."}), 500

        # Return the structured JSON response
        return jsonify({"categories": categories_services}), 200

    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500
    

    
