import traceback
from flask import Blueprint, jsonify, request
from datetime import datetime

from database.get_bookings_from_today_onwards.get_bookings_from_today_onwards import get_bookings_from_today_onwards
from database.insert_booking.insert_booking import insert_booking


insert_booking_bp = Blueprint('insert_booking_bp', __name__)

@insert_booking_bp.route('/bookings', methods=['POST'])
def create_booking():
    try:
        data = request.json
        barber_id = data['barber_id']
        service_id = data['service_id']
        customer_name = data['customer_name']
        appointment_time = datetime.fromisoformat(data['appointment_time'])
        email = data['email']
        phone = data['phone']
        price = data['price']
        extra = data['extra']

        success, message = insert_booking(barber_id, service_id, customer_name, appointment_time, email, phone, price, extra)
        
        if success:
            return jsonify({"status": "success", "message": message}), 201
        else:
            return jsonify({ "message": message}), 409 if "Time slot unavailable" in message else 500

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500




get_todays_bookings_bp = Blueprint('get_todays_bookings_bp', __name__)

@get_todays_bookings_bp.route('/get_todays_bookings', methods=['GET'])
def get_todays_bookings():
    try:
        barber_id = request.args.get('barber_id')
        if not barber_id:
            return jsonify({'error': 'Barber ID is required.'}), 400

        success, result = get_bookings_from_today_onwards(barber_id)

        if success:
            return jsonify({'bookings': result}), 200
        else:
            return jsonify({'error': result}), 500

    except Exception as e:
        # Log the specific error message
        print(f"Error occurred in /get_todays_bookings route: {e}")
        traceback.print_exc() 
        return jsonify({'error': f"An internal error occurred: {str(e)}"}), 500
