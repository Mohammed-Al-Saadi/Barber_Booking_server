
def get_barbers_for_service(service_names):
    """Get all barbers and the total estimated time for the list of services."""
    conn = get_connection()  # Use get_connection() to get a connection from the pool

    if conn:
        try:
            cursor = conn.cursor()

            # Create a query that accepts multiple service names using the IN clause
            query = f"""
                SELECT DISTINCT s.service_name, s.estimated_time, b.barber_id, b.name
                FROM Barbers b
                JOIN BarberServices bs ON b.barber_id = bs.barber_id
                JOIN Services s ON bs.service_id = s.service_id
                WHERE s.service_name IN %s;
            """

            # Format the service names as a tuple to pass it to the query
            service_names_tuple = tuple(service_names)

            # Execute the query
            cursor.execute(query, (service_names_tuple,))

            # Fetch the results
            results = cursor.fetchall()

            # Close the cursor and release the connection
            cursor.close()
            release_connection(conn)

            # If there are no results, return an empty response
            if not results:
                return None

            # Initialize a set for unique barbers and calculate the total estimated time for all services
            barbers = {}
            total_estimated_time = 0  # Initialize total time for all services
            seen_services = set()  # To ensure we only sum the time for each service once

            for row in results:
                service_name = row[0]
                estimated_time = row[1].total_seconds() / 60 if isinstance(row[1], timedelta) else row[1]
                barber_id = row[2]
                barber_name = row[3]

                # Add the barber to the dictionary if they aren't already there
                if barber_id not in barbers:
                    barbers[barber_id] = barber_name

                # Accumulate the estimated time for distinct services only
                if service_name not in seen_services:
                    total_estimated_time += estimated_time
                    seen_services.add(service_name)

            # Convert the dictionary of barbers to a list
            barbers_list = [{"barber_id": barber_id, "name": name} for barber_id, name in barbers.items()]

            # Return all barbers and the total estimated time for the services
            return {
                "barbers": barbers_list,
                "estimated_time": total_estimated_time  # Total time for all distinct services
            }

        except Exception as e:
            release_connection(conn)
            print(f"Error occurred: {e}")
            return None
    else:
        print("Failed to connect to the database")
        return None


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
        service_id = db_config.get_service_id(service_name=service_name)

        if not service_id:
            return jsonify({"error": "Service ID not found."}), 404

        # Fetch data from the database for time slot generation and prices
        barber_schedules, barber_dates, existing_bookings, exceptions, barber_prices = db_config.fetch_barber_data_from_db(service_id=service_id)

        # Generate time slots
        time_slots_by_barber = generate_barber_specific_slots_with_bookings(
            barber_schedules, barber_dates, existing_bookings, barber_ids=barber_ids, 
            gap_minutes=gap_minutes, exceptions=exceptions, service_duration_minutes=estimated_time_minutes
        )

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



def fetch_barber_data_from_db(service_id=None):
    """
    Fetch barber schedules, availability dates, existing bookings, exceptions, and service prices from the database.
    
    Parameters:
    - service_id (int, optional): The ID of the service to fetch prices for.
    
    Returns:
    - barber_schedules (dict): Barber IDs mapped to their working hours.
    - barber_dates (dict): Barber IDs mapped to their availability date ranges.
    - existing_bookings (dict): Barber IDs mapped to their existing bookings.
    - exceptions (dict): Barber-specific exceptions for custom working hours or days off.
    - barber_prices (dict): Barber IDs mapped to the price of the specified service.
    """
    conn = get_connection() 
    if not conn:
        print("Failed to connect to the database")
        return None, None, None, None, None  # Updated to include barber_prices
    
    try:
        cur = conn.cursor()

        # Fetch barber schedules
        cur.execute("SELECT barber_id, start_time, end_time FROM BarberSchedules")
        barber_schedules = {row[0]: (row[1].strftime('%H:%M'), row[2].strftime('%H:%M')) for row in cur.fetchall()}

        # Fetch barber availability dates
        cur.execute("SELECT barber_id, start_date, end_date FROM BarberAvailability")
        barber_dates = {row[0]: (row[1], row[2]) for row in cur.fetchall()}

        # Fetch existing bookings along with the service duration
        cur.execute("""
            SELECT b.barber_id, b.appointment_time, s.estimated_time
            FROM Bookings b
            JOIN Services s ON b.service_id = s.service_id
        """)
        existing_bookings = {}
        for row in cur.fetchall():
            barber_id, appointment_time, estimated_time = row
            if barber_id not in existing_bookings:
                existing_bookings[barber_id] = []
            existing_bookings[barber_id].append((appointment_time.strftime('%Y-%m-%d %H:%M:%S'), estimated_time))

        # Fetch exceptions
        cur.execute("SELECT barber_id, exception_date, custom_start_time, custom_end_time, is_off FROM BarberExceptions")
        exceptions = {}
        for row in cur.fetchall():
            barber_id, exception_date, custom_start, custom_end, is_off = row
            date_str = exception_date.strftime('%Y-%m-%d')
            if date_str not in exceptions:
                exceptions[date_str] = {}
            if is_off:
                exceptions[date_str][barber_id] = None
            else:
                exceptions[date_str][barber_id] = (custom_start.strftime('%H:%M'), custom_end.strftime('%H:%M'))

        # Fetch barber service prices if a service_id is provided
        barber_prices = {}
        if service_id is not None:
            cur.execute("""
                SELECT barber_id, price FROM BarberServicePrices 
                WHERE service_id = %s
            """, (service_id,))
            barber_prices = {row[0]: float(row[1]) for row in cur.fetchall()}

        cur.close()
        return barber_schedules, barber_dates, existing_bookings, exceptions, barber_prices

    except Exception as e:
        print(f"Error occurred while fetching barber data: {e}")
        return None, None, None, None, None  # Updated to include barber_prices

    finally:
        # Release the connection back to the pool
        release_connection(conn)
