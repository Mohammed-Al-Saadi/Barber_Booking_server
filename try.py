
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




def update_booking_with_extra_service(booking_id, extra_service_id):
    """
    Update the extra services for a specific booking, ensuring that the extended time does not overlap with the next booking.

    Parameters:
    - booking_id (int): The ID of the booking to update.
    - extra_service_id (int): The ID of the extra service to add.

    Returns:
    - A tuple (success, message), where success is a boolean indicating if the operation was successful,
      and message is a string indicating the result.
    """
    conn = get_connection()
    if not conn:
        return False, "Failed to connect to the database."

    try:
        cursor = conn.cursor()

        # 1. Fetch the current booking details
        cursor.execute("""
            SELECT barber_id, appointment_time, service_id, extra 
            FROM Bookings 
            WHERE booking_id = %s
        """, (booking_id,))
        booking = cursor.fetchone()

        if not booking:
            return False, "Booking not found."

        barber_id, appointment_time, service_id, extra_services = booking

        # If extra_services is None, initialize it as an empty list
        if extra_services is None:
            extra_services = []

        # 2. Fetch the estimated time of the main service
        cursor.execute("""
            SELECT estimated_time 
            FROM Services 
            WHERE service_id = %s
        """, (service_id,))
        main_service_time = cursor.fetchone()

        if not main_service_time:
            return False, "Main service not found."

        # Convert main_service_time to minutes (handle timedelta or None)
        main_service_minutes = main_service_time[0].total_seconds() / 60 if main_service_time[0] else 0

        # 3. Fetch the estimated time for the extra service (the new one being added)
        cursor.execute("""
            SELECT estimated_time 
            FROM Services 
            WHERE service_id = %s
        """, (extra_service_id,))
        extra_service_time = cursor.fetchone()

        if not extra_service_time:
            return False, "Extra service not found."

        # Convert extra_service_time to minutes
        extra_service_minutes = extra_service_time[0].total_seconds() / 60 if extra_service_time[0] else 0

        # 4. Fetch the next booking for the barber on the same date
        cursor.execute("""
            SELECT appointment_time
            FROM Bookings
            WHERE barber_id = %s AND appointment_time > %s
            ORDER BY appointment_time ASC
            LIMIT 1
        """, (barber_id, appointment_time))
        next_booking = cursor.fetchone()

        if next_booking:
            next_booking_time = next_booking[0]
        else:
            next_booking_time = None  # No next booking, so the barber is free after the current booking

        # 5. Calculate total time for the current booking with the extra service
        total_estimated_time = main_service_minutes

        # 6. Add the estimated times for existing extra services
        if extra_services:
            # Convert the list of extra services to a PostgreSQL array using ARRAY[]
            cursor.execute("""
                SELECT estimated_time 
                FROM Services 
                WHERE service_id = ANY(ARRAY[%s]::int[])
            """ % ','.join(map(str, extra_services)))  # Convert list to comma-separated string for SQL array
            extra_services_times = cursor.fetchall()
            for extra_time in extra_services_times:
                if extra_time[0]:
                    total_estimated_time += extra_time[0].total_seconds() / 60

        # Add the new extra service time
        total_estimated_time += extra_service_minutes

        # Calculate the end time of the current booking with the extra service
        current_booking_end = appointment_time + timedelta(minutes=total_estimated_time)

        # 7. Check if the extended time overlaps with the next booking
        if next_booking_time and current_booking_end > next_booking_time:
            return False, "Not enough time available before the next booking."

        # 8. Update the extra services and extend the booking time
        if extra_service_id not in extra_services:
            extra_services.append(extra_service_id)  # Add the new extra service

        # Update the booking with the new extra services
        cursor.execute("""
            UPDATE Bookings
            SET extra = %s
            WHERE booking_id = %s
        """, (extra_services, booking_id))

        # Commit the transaction
        conn.commit()

        return True, "Extra service added successfully."

    except Exception as e:
        conn.rollback()
        print(f"Error occurred: {e}")
        return False, "An error occurred while updating the booking."

    finally:
        cursor.close()
        release_connection(conn)







from datetime import datetime, time, timedelta
from database.db_config import get_existing_breaks_for_barber

def generate_barber_specific_slots_with_bookings(
    barber_schedules, barber_dates, existing_bookings, barber_ids=None, 
    gap_minutes: int = 15, exceptions: dict = None, service_duration_minutes: int = None
):
    # Normalize barber_ids to a list if it's a single int
    if isinstance(barber_ids, int):
        barber_ids = [barber_ids]
    elif barber_ids is None:
        barber_ids = list(barber_schedules.keys())
    
    slots_by_barber = {barber_id: {} for barber_id in barber_ids}

    for barber_id in barber_ids:
        # Get the default start and end times for this barber
        default_start_time, default_end_time = barber_schedules.get(barber_id, ('00:00', '00:00'))
        
        # Get the start and end dates specific to this barber
        start_date, end_date = barber_dates.get(barber_id, (None, None))
        
        # If start_date or end_date is not provided, set default values
        if start_date is None:
            start_date = datetime.now().date()  # Set start date to current date
        if end_date is None:
            end_date = start_date + timedelta(days=10)  # Set end date to 2 days from the start date

        current_date = start_date

        while current_date <= end_date:
            current_date_str = current_date.strftime('%Y-%m-%d')

            # Handle exceptions (custom hours or exclusion) for specific days
            if exceptions and current_date_str in exceptions and barber_id in exceptions[current_date_str]:
                custom_times = exceptions[current_date_str][barber_id]
                if custom_times is None:
                    current_date += timedelta(days=1)
                    continue
                else:
                    start_hour, start_minute = map(int, custom_times[0].split(':'))
                    end_hour, end_minute = map(int, custom_times[1].split(':'))
            else:
                start_hour, start_minute = map(int, default_start_time.split(':'))
                end_hour, end_minute = map(int, default_end_time.split(':'))

            # Create datetime objects for start and end times
            start_time = datetime.combine(current_date, time(start_hour, start_minute))
            end_time = datetime.combine(current_date, time(end_hour, end_minute))
            slots = []

            # Fetch bookings for this barber on this date
            barber_bookings = existing_bookings.get(barber_id, [])
            barber_bookings_today = [(datetime.strptime(booking_time, '%Y-%m-%d %H:%M:%S'), service_duration) 
                                     for booking_time, service_duration in barber_bookings 
                                     if datetime.strptime(booking_time, '%Y-%m-%d %H:%M:%S').date() == current_date]

            # Sort the bookings by appointment time
            barber_bookings_today.sort(key=lambda x: x[0])

            # Get the current time
            current_datetime = datetime.now()

            # Fetch barber's break times for this date
            break_times = get_existing_breaks_for_barber(barber_id, current_date)

            # Generate slots while checking for bookings and breaks
            for booking_time, booking_duration in barber_bookings_today:
                if isinstance(booking_duration, timedelta):
                    booking_duration = int(booking_duration.total_seconds() / 60)

                while start_time + timedelta(minutes=service_duration_minutes) <= booking_time:
                    # Skip expired slots if it's the current day
                    if current_date == current_datetime.date() and start_time < current_datetime:
                        start_time += timedelta(minutes=gap_minutes)
                        continue
                    
                    # Format start_time as 'HH:MM' to compare with breaks
                    formatted_start_time = start_time.strftime('%H:%M')

                    # Only append the slot if it doesn't match a break time
                    if formatted_start_time not in break_times:
                        slots.append((start_time, start_time + timedelta(minutes=service_duration_minutes)))
                    
                    start_time += timedelta(minutes=gap_minutes)

                start_time = booking_time + timedelta(minutes=booking_duration)

            # Generate remaining slots after the last booking
            while start_time + timedelta(minutes=service_duration_minutes) <= end_time:
                # Skip expired slots if it's the current day
                if current_date == current_datetime.date() and start_time < current_datetime:
                    start_time += timedelta(minutes=gap_minutes)
                    continue

                # Format start_time as 'HH:MM' to compare with breaks
                formatted_start_time = start_time.strftime('%H:%M')

                # Only add the slot if it fits within operating hours and is not a break time
                if formatted_start_time not in break_times:
                    slots.append((start_time, start_time + timedelta(minutes=service_duration_minutes)))
                
                start_time += timedelta(minutes=gap_minutes)

            slots_by_barber[barber_id][current_date_str] = slots
            current_date += timedelta(days=1)

    return slots_by_barber
