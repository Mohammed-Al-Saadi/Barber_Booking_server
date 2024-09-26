from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta, time
from srvices.barbers_slots_main import generate_barber_specific_slots_with_bookings
from database import db_config
from srvices.jwt_models import generate_token

from flask import Flask, request, jsonify
from datetime import datetime
import jwt
SECRET_KEY = "ndwdkw-defdef-fefefe"
# Flask app initialization
app = Flask(__name__)

# Enable CORS for all origins and allow credentials
CORS(app, supports_credentials=True, origins=["*"])
from datetime import datetime, timedelta, time

# route to create account
@app.route('/signup', methods=['POST'])
def signup():
    barber_id = request.json.get('barber_id')
    username = request.json.get('username')
    password = request.json.get('password')

    if not barber_id or not username or not password:
        return jsonify({'error': 'Barber ID, username, and password are required!'}), 400

    result = db_config.create_user(barber_id, username, password)

    if result == "success":
        return jsonify({'message': 'User created successfully!'}), 201
    elif result == "barber_exists":
        return jsonify({'error': 'Barber ID already exists!'}), 409
    elif result == "username_exists":
        return jsonify({'error': 'Username already exists!'}), 409

# route to login
@app.route('/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required!'}), 400

    result, barber_id = db_config.verify_user(username, password)  # Ensure verify_user returns barber_id

    if result == "login_success":
        token = generate_token(barber_id)  # Generate a token with barber_id
        return jsonify({'message': 'Login successful!', 'token': token}), 200
    elif result == "user_not_found":
        return jsonify({'error': 'Username does not exist!'}), 404
    elif result == "invalid_password":
        return jsonify({'error': 'Incorrect password!'}), 401
    


# route to protect dash
@app.route('/protected', methods=['GET'])
def protected_route():
    # Get the token from the Authorization header
    token = request.headers.get('Authorization')
    
    if not token:
        return jsonify({'message': 'Token is missing!'}), 401
    
    try:
        # Split the token from "Bearer <token>"
        token = token.split(" ")[1]
        data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])

        # Get the expiration date from the token
        exp = datetime.utcfromtimestamp(data['exp']).strftime('%Y-%m-%d %H:%M:%S')

        return jsonify({
            'id':data["barber_id"],
            'expiration_date': exp  # Include the expiration date
        })
    except jwt.ExpiredSignatureError:
        return jsonify({'message': 'Token has expired!'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'message': 'Token is invalid!'}), 401



#route get barber for the service and time slots
@app.route('/get_barbers_and_slots', methods=['POST'])
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
        barbers_data = db_config.get_barbers_for_service( service_names=service_name)

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
        service_id = db_config.get_service_id(service_name)

        if not service_id:
            return jsonify({"error": "Service ID not found."}), 404

        # Fetch data from the database for time slot generation and prices
        barber_schedules, barber_dates, existing_bookings, exceptions, barber_prices = db_config.fetch_barber_data_from_db(service_ids=service_id)

        # Generate time slots
        time_slots_by_barber = generate_barber_specific_slots_with_bookings(
            barber_schedules, barber_dates, existing_bookings, barber_ids=barber_ids, 
            gap_minutes=gap_minutes, exceptions=exceptions, service_duration_minutes=estimated_time_minutes
        )
        print("ssssss",existing_bookings)


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



# route to get categories and services
@app.route('/get_categories_and_services', methods=['GET'])
def get_categories_and_services():
    try:
        # Call the database function to fetch categories and services
        categories_services = db_config.fetch_categories_and_services()

        # Check if there was an error during fetching
        if categories_services is None:
            return jsonify({"error": "An error occurred while fetching categories and services."}), 500

        # Return the structured JSON response
        return jsonify({"categories": categories_services}), 200

    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500
    

    


# route to insert booking 
@app.route('/bookings', methods=['POST'])
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

        
        success, message = db_config.insert_booking(barber_id, service_id, customer_name, appointment_time, email, phone, price, extra)
        
        if success:
            return jsonify({"status": "success", "message": message}), 201
        else:
            # If the message indicates a conflict, return a 409 (Conflict) status code
            return jsonify({ "message": message}), 409 if "Time slot unavailable" in message else 500

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# route to set barber break time 
@app.route('/set_barber_break_slots', methods=['POST'])
def set_barber_break_slots():
    try:
        data = request.json
        barber_id = data['barber_id']
        break_date = datetime.fromisoformat(data['break_date']).date()
        break_slots = data['break_slots']  # List of break slots in "HH:MM" format

        # Ensure that the time slots are valid and don't overlap with existing bookings
        existing_bookings = db_config.get_bookings_for_barber(barber_id, break_date)
        for slot in break_slots:
            break_time = datetime.combine(break_date, datetime.strptime(slot, "%H:%M").time())

            # Check if the selected break slot overlaps with existing bookings
            for booking in existing_bookings:
                appointment_time = booking['appointment_time']
                service_duration = timedelta(minutes=booking['service_duration'])
                booking_end_time = appointment_time + service_duration

                if break_time >= appointment_time and break_time < booking_end_time:
                    return jsonify({"error": f"Break time {slot} overlaps with an existing booking."}), 409

        # Insert the break slots into the BarberBreaks table
        for slot in break_slots:
            break_time = datetime.strptime(slot, "%H:%M").time()
            db_config.insert_barber_break_slot(barber_id, break_date, break_time)

        return jsonify({"status": "success", "message": "Break slots added successfully."}), 201

    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

# Entry point for running the app in development mode (auto-reloading)
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
