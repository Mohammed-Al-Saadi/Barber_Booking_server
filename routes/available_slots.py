

from datetime import datetime
from flask import Blueprint, jsonify, request

from database.get_available_free_slots.get_available_free_slots import get_available_free_slots
available_slots_bp = Blueprint('available_slots_bp', __name__)


@available_slots_bp.route('/available-slots', methods=['GET'])
def available_slots():
    """
    API route to fetch available time slots for a specific barber and date.
    
    Query Parameters:
    - barber_id: ID of the barber (required)
    - date: Date in "YYYY-MM-DD" format (required)
    """
    # Fetch query parameters from the URL
    barber_id = request.args.get('barber_id')
    date_str = request.args.get('date')

    if not barber_id or not date_str:
        return jsonify({"error": "Missing barber_id or date parameter"}), 400

    try:
        # Convert barber_id to int and strip any whitespace/newline characters from date_str
        barber_id = int(barber_id)
        date_str = date_str.strip()  # Strip leading/trailing whitespaces and newlines
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as e:
        return jsonify({"error": f"Invalid input: {e}"}), 400

    # Fetch the available slots using the function
    available_slots = get_available_free_slots(barber_id, date)
    
    # Return the result as JSON
    return jsonify({"available_slots": available_slots})



