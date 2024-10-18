
from datetime import datetime

from flask import Blueprint, jsonify, request

from database.get_appointments_and_breaks.get_appointments_and_breaks import get_appointments_and_breaks

over_all_bp = Blueprint('over_all_bp', __name__)

@over_all_bp.route('/barber', methods=['GET'])
def fetch_appointments_and_breaks():
    # Get the barber_id and date from query parameters
    barber_id = request.args.get('barber_id')
    requested_date = request.args.get('date', None)

    # Validate that barber_id is provided
    if not barber_id:
        return jsonify({"error": "barber_id is required"}), 400

    # Default to today's date if no date is provided
    if requested_date:
        try:
            # Convert the date to a datetime object
            selected_date = datetime.strptime(requested_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400
    else:
        selected_date = datetime.now().date()  # Use today's date as default

    # Call the function to fetch appointments and breaks for the barber on the selected date
    data = get_appointments_and_breaks(barber_id, selected_date)

    # Return the fetched data (or an empty list if no data found)
    return jsonify(data if data else ["No data"]), 200

