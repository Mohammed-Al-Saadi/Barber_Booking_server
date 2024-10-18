
from flask import Blueprint, jsonify, request

from database.barber_exceptions.barber_exceptions import get_barber_exceptions, insert_barber_exception

insert_barber_exception_bp = Blueprint('insert_barber_exception_bp', __name__)

@insert_barber_exception_bp.route('/insert_barber_exception', methods=['POST'])
def insert_barber_exception_route():
    """
    Route to insert a new record into BarberExceptions.

    Expects a JSON body:
    {
        "barber_id": int,
        "exception_date": "YYYY-MM-DD",
        "custom_start_time": "HH:MM:SS", (optional)
        "custom_end_time": "HH:MM:SS", (optional)
        "is_off": bool
    }

    Returns:
    - 200 if the insert/update was successful.
    - 400 if there's an issue with the input data.
    - 500 if an error occurred during the insert.
    """
    try:
        # Get JSON data from the request
        data = request.get_json()

        # Log the incoming data for debugging
        print(f"Received data: {data}")

        # Extract and validate the data from the JSON body
        barber_id = data.get('barber_id')
        exception_date = data.get('exception_date')
        custom_start_time = data.get('custom_start_time')  # Optional
        custom_end_time = data.get('custom_end_time')  # Optional
        is_off = data.get('is_off', False)  # Defaults to False if not provided

        # Validate required fields
        if not barber_id or not exception_date:
            return jsonify({"error": "Missing barber_id or exception_date"}), 400

        # Call the insert function
        if insert_barber_exception(barber_id, exception_date, custom_start_time, custom_end_time, is_off):
            return jsonify({"message": "Barber exception inserted successfully"}), 200
        else:
            return jsonify({"error": "Failed to insert barber exception"}), 500

    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({"error": str(e)}), 500


get_barber_exceptions_bp = Blueprint('get_barber_exceptions_bp', __name__)
@get_barber_exceptions_bp.route('/get_barber_exceptions', methods=['GET'])
def get_barber_exceptions_route():
    """
    Flask route to fetch all future barber exceptions based on barber_id.

    Query Parameters:
    - barber_id (int): The ID of the barber (passed via query string).

    Returns:
    - JSON: List of barber exceptions.
    """
    try:
        # Get the barber_id from query parameters
        barber_id = request.args.get('barber_id')
        
        if not barber_id:
            return jsonify({"error": "barber_id is required"}), 400
        
        # Fetch the barber exceptions
        exceptions = get_barber_exceptions(barber_id)
        
        if exceptions is None:
            return jsonify({"error": "Failed to fetch barber exceptions"}), 500
        
        return jsonify(exceptions), 200

    except Exception as e:
        print(f"Error occurred in route: {e}")
        return jsonify({"error": str(e)}), 500
    


    