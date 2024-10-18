from datetime import datetime
from flask import Blueprint, jsonify, request

from database.delete_barber_break.delete_barber_break import delete_barber_break
from database.get_existing_breaks_for_barber.get_existing_breaks_for_barber import get_barber_breaks
from database.insert_barber_break_slot.insert_barber_break_slot import insert_barber_break_slot

get_barber_breaks_bp = Blueprint('get_barber_breaks_bp', __name__)


@get_barber_breaks_bp.route('/get_barber_breaks', methods=['GET'])
def barber_breaks_route():
    """
    Route to get all breaks for a specific barber.
    Optionally filters by break type if 'type' is provided.
    """
    barber_id = request.args.get('barber_id', type=int)
    break_type = request.args.get('type')  # Optional type parameter

    if barber_id is None:
        return jsonify({"success": False, "message": "barber_id is required"}), 400

    # Call the function and pass the optional break_type
    success, result = get_barber_breaks(barber_id, break_type)

    if success:
        return jsonify({"success": True, "breaks": result}), 200
    else:
        return jsonify({"success": False, "message": result}), 500
    


add_barber_breaks_bp = Blueprint('add_barber_breaks_bp', __name__)


@add_barber_breaks_bp.route('/add_barber_break_slot', methods=['POST'])
def add_barber_break_slot():
    """
    Route to add one or multiple barber break slots.
    Expects JSON with barber_id, break_date, break_time (can be a single value or an array of times), and type.
    """
    try:
        data = request.json
        barber_id = data.get('barber_id')
        break_date = data.get('break_date')
        break_time = data.get('break_time')
        timeType = data.get('timeType')  
        booking_id = data.get('booking_id') 


        # Check if all fields are provided
        if barber_id is None or break_date is None or break_time is None or timeType is None or booking_id is None:
            return jsonify({"success": False, "message": "Missing data."}), 400

        # Convert break_date to date object if necessary (depending on how break_date is formatted)
        try:
            break_date = datetime.strptime(break_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"success": False, "message": "Invalid date format. Use YYYY-MM-DD."}), 400

        # Ensure break_time is a list, even if a single value is provided
        if isinstance(break_time, str):
            break_time = [break_time]  # Convert single time into a list
        elif isinstance(break_time, list):
            pass  # Already a list, so continue
        else:
            return jsonify({"success": False, "message": "Invalid break_time format."}), 400

        # Convert each break_time string to a time object (assuming 'HH:MM' format)
        try:
            break_times = [datetime.strptime(time_str, '%H:%M').time() for time_str in break_time]
        except ValueError:
            return jsonify({"success": False, "message": "Invalid time format. Use HH:MM."}), 400

        # Call the function to insert the break slots
        success = insert_barber_break_slot(barber_id, break_date, break_times, timeType, booking_id= booking_id)

        if success:
            return jsonify({"success": True, "message": "Break slots added successfully."}), 201
        else:
            return jsonify({"success": False, "message": "Failed to add break slots."}), 500

    except Exception as e:
        print(f"Error in add_barber_break_slot: {e}")  # Log the error
        return jsonify({"success": False, "message": "An error occurred."}), 500
    


delete_barber_break_bp = Blueprint('delete_barber_break_bp', __name__)


@delete_barber_break_bp.route('/delete_barber_break', methods=['DELETE'])
def delete_barber_break_route():
    try:
        break_id = request.args.get('break_id')

        if break_id is None:
            return jsonify({"success": False, "message": "Missing break_id."}), 400

        success = delete_barber_break(int(break_id))

        if success:
            return jsonify({"success": True, "message": "Break slot deleted successfully."}), 200
        else:
            return jsonify({"success": False, "message": "Failed to delete break slot."}), 500

    except Exception as e:
        print(f"Error in delete_barber_break_route: {e}")
        return jsonify({"success": False, "message": "An error occurred."}), 500


