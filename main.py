from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta, time
from srvices.barbers_slots_main import generate_barber_specific_slots_with_bookings
from database import db_config
from srvices.jwt_models import generate_token
from database.db_config import  get_appointments_and_breaks, get_barber_data, get_bookings_from_today_onwards,update_booking_price, get_barber_breaks,insert_barber_break_slot,delete_barber_break,get_barber_name_by_id,get_barber_schedule,update_barber_schedule,insert_barber_exception,get_barber_exceptions,get_available_free_slots

from flask import Flask, request, jsonify
from datetime import datetime
import jwt

# Define the Finland timezone
import jwt
import pytz

SECRET_KEY = "ndwdkw-defdef-fefefe"
# Flask app initialization
app = Flask(__name__)
finland_tz = pytz.timezone('Europe/Helsinki')

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

        # Get the expiration timestamp from the token
        exp_timestamp = data['exp']

        # Convert the UTC expiration time to Finland time
        utc_expiration = datetime.utcfromtimestamp(exp_timestamp)
        finland_expiration = utc_expiration.replace(tzinfo=pytz.utc).astimezone(finland_tz)

        # Format the expiration time for Finland
        exp = finland_expiration.strftime('%Y-%m-%d %H:%M:%S')

        # Extract barber_id from the decoded JWT data
        barber_id = data.get('barber_id')

        if not barber_id:
            return jsonify({'message': 'Barber ID not found in token!'}), 400

        # Fetch the barber's name using the barber_id
        barber_name = get_barber_name_by_id(barber_id)

        if not barber_name:
            return jsonify({'message': 'Barber not found!'}), 404

        return jsonify({
            'barber_id': barber_id,
            'barber_name': barber_name,
            'expiration_date': exp  # Include the expiration date in Finland time
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




@app.route('/get_todays_bookings', methods=['GET'])
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
        traceback.print_exc()  # This will print the full traceback in the console
        return jsonify({'error': f"An internal error occurred: {str(e)}"}), 500

@app.route('/get_barber_breaks', methods=['GET'])
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

@app.route('/add_barber_break_slot', methods=['POST'])
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

@app.route('/delete_barber_break', methods=['DELETE'])
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






# Define the route to fetch the barber schedule
@app.route('/get_barber_schedule', methods=['GET'])
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





@app.route('/update_barber_schedule', methods=['POST'])
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


@app.route('/insert_barber_exception', methods=['POST'])
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




@app.route('/get_barber_exceptions', methods=['GET'])
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

@app.route('/available-slots', methods=['GET'])
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






@app.route('/update_price', methods=['POST'])
def update_price():
    """
    Route to update the price of a booking.
    
    Expected JSON body:
    {
        "booking_id": <int>,
        "new_price": <float>
    }
    
    Returns:
    - JSON response with success status and message.
    """
    try:
        # Get the JSON data from the request
        data = request.get_json()

        # Extract booking_id and new_price from the request body
        booking_id = data.get('booking_id')
        new_price = data.get('new_price')

        if not booking_id or new_price is None:
            return jsonify(success=False, message="Missing booking_id or new_price"), 400

        # Call the update_booking_price function to update the price
        success, message = update_booking_price(booking_id, new_price)

        # Return a success or error message based on the result
        if success:
            return jsonify(success=True, message=message), 200
        else:
            return jsonify(success=False, message=message), 400

    except Exception as e:
        return jsonify(success=False, message=f"An error occurred: {str(e)}"), 500
@app.route('/barber', methods=['GET'])
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



# Entry point for running the app in development mode (auto-reloading)
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
