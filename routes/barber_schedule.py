
# Define the route to fetch the barber schedule
from flask import Blueprint, jsonify, request

from database.barber_schedule.get_barber_schedule import get_barber_schedule, update_barber_schedule

get_barber_schedule_bp = Blueprint('get_barber_schedule_bp', __name__)

@get_barber_schedule_bp.route('/get_barber_schedule', methods=['GET'])
def barber_schedule():
    # Get barber_id from query parameters
    barber_id = request.args.get('barber_id')

    if not barber_id:
        return jsonify({"error": "barber_id is required"}), 400

    try:
        barber_id = int(barber_id)  # Convert barber_id to integer
    except ValueError:
        return jsonify({"error": "Invalid barber_id"}), 400

    # Fetch the barber's schedule using the function
    schedule = get_barber_schedule(barber_id)

    if schedule:
        start_time, end_time = schedule
        return jsonify({
            "barber_id": barber_id,
            "start_time": str(start_time),
            "end_time": str(end_time)
        }), 200
    else:
        return jsonify({"error": f"No schedule found for barber with ID {barber_id}"}), 404




update_barber_schedule_bp = Blueprint('update_barber_schedule_bp', __name__)

@update_barber_schedule_bp.route('/update_barber_schedule', methods=['POST'])
def update_schedule():
    """
    API route to update the start and end times for a barber's schedule.

    Expects JSON input:
    {
        "barber_id": int,
        "start_time": "HH:MM:SS",
        "end_time": "HH:MM:SS"
    }

    Returns:
    - 200 if the update was successful.
    - 400 if there's an issue with the input data.
    - 500 if there's an error updating the schedule.
    """
    try:
        # Get JSON data from the request
        data = request.get_json()

        # Extract data from the request
        barber_id = data.get("barber_id")
        start_time = data.get("start_time")
        end_time = data.get("end_time")

        # Validate the input data
        if not all([barber_id, start_time, end_time]):
            return jsonify({"error": "Missing barber_id, start_time, or end_time"}), 400

        # Call the update function
        if update_barber_schedule(barber_id, start_time, end_time):
            return jsonify({"message": "Barber schedule updated successfully"}), 200
        else:
            return jsonify({"error": "Failed to update barber schedule"}), 500

    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({"error": str(e)}), 500
