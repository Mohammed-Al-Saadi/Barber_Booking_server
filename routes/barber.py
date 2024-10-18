from datetime import datetime, timedelta  # Correct import for timedelta
from flask import Blueprint, jsonify, request

from database.get_barber_data.fetch_barber_data_from_db import fetch_barber_data_from_db
from database.get_barbers_for_service.get_barbers_for_service import get_barbers_for_service
from database.get_bookings_for_barber.get_bookings_for_barber import get_bookings_for_barber
from database.get_service_id.get_service_id import get_service_id
from database.insert_barber_break_slot.insert_barber_break_slot import insert_barber_break_slot
from srvices.bookings.barbers_slots_main import generate_barber_specific_slots_with_bookings

barbers_and_slots_bp = Blueprint('barbers_and_slots_bp', __name__)

# Route to get barber for the service and time slots
@barbers_and_slots_bp.route('/get_barbers_and_slots', methods=['POST'])
def get_barbers_and_slots():
    try:
        # Get the category and service from the request body
        data = request.json
        service_name = data.get('service_name')
        gap_minutes = data.get('gap_minutes', 15)
        
        # Validate input
        if not service_name or not isinstance(service_name, list) or len(service_name) == 0:
            return jsonify({"error": "'service_name' must be a non-empty array."}), 400

        # Get the barbers for the given service
        barbers_data = get_barbers_for_service(service_names=service_name)

        # Check if the call to the database returned an error
        if barbers_data is None:
            return jsonify({"error": "An error occurred while fetching barbers."}), 500

        # Check if no barbers were found
        if not barbers_data['barbers']:
            return jsonify({"error": "No barbers found for the given service."}), 404

        # Extract barber IDs and estimated time (convert to minutes)
        barber_ids = [barber['barber_id'] for barber in barbers_data['barbers']]
        estimated_time = barbers_data['estimated_time']
        estimated_time_minutes = int(estimated_time.total_seconds() / 60) if isinstance(estimated_time, timedelta) else estimated_time

        # Fetch the service ID for the given category and service
        service_id = get_service_id(service_name)

        if not service_id:
            return jsonify({"error": "Service ID not found."}), 404

        # Fetch data from the database for time slot generation and prices
        barber_schedules, barber_dates, existing_bookings, exceptions, barber_prices = fetch_barber_data_from_db(service_ids=service_id)

        # Generate time slots
        time_slots_by_barber = generate_barber_specific_slots_with_bookings(
            barber_schedules, barber_dates, existing_bookings, barber_ids=barber_ids, 
            gap_minutes=gap_minutes, exceptions=exceptions, service_duration_minutes=estimated_time_minutes
        )
        print("ssssss", existing_bookings)

        # Prepare the final response
        response = {
            "barbers": {
                "barbers": [
                    {**barber, "price": barber_prices.get(barber['barber_id'])} for barber in barbers_data['barbers']
                ],
                "estimated_time": estimated_time,
                "time_slots": {
                    barber_id: {
                        day: [{"Time": slot[0].strftime('%H:%M')} for slot in slots]
                        for day, slots in days.items()
                    } for barber_id, days in time_slots_by_barber.items()
                }
            }
        }

        return jsonify(response), 200

    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


# Blueprint for setting barber break slots
set_barber_break_slots_bp = Blueprint('set_barber_break_slots_bp', __name__)

# Route to set barber break time 
@set_barber_break_slots_bp.route('/set_barber_break_slots', methods=['POST'])
def set_barber_break_slots():
    try:
        data = request.json
        barber_id = data['barber_id']
        break_date = datetime.fromisoformat(data['break_date']).date()
        break_slots = data['break_slots']  # List of break slots in "HH:MM" format

        # Ensure that the time slots are valid and don't overlap with existing bookings
        existing_bookings = get_bookings_for_barber(barber_id, break_date)
        for slot in break_slots:
            break_time = datetime.combine(break_date, datetime.strptime(slot, "%H:%M").time())

            # Check if the selected break slot overlaps with existing bookings
            for booking in existing_bookings:
                appointment_time = booking['appointment_time']
                service_duration = timedelta(minutes=booking['service_duration'])  # Corrected timedelta usage
                booking_end_time = appointment_time + service_duration

                if break_time >= appointment_time and break_time < booking_end_time:
                    return jsonify({"error": f"Break time {slot} overlaps with an existing booking."}), 409

        # Insert the break slots into the BarberBreaks table
        for slot in break_slots:
            break_time = datetime.strptime(slot, "%H:%M").time()
            insert_barber_break_slot(barber_id, break_date, break_time)

        return jsonify({"status": "success", "message": "Break slots added successfully."}), 201

    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500
