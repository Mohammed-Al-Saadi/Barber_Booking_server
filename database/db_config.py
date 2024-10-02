# db_connection.py
import hashlib
import os
import traceback
import psycopg2
from psycopg2 import pool
from datetime import date, datetime, time, timedelta


# Database connection details
DB_USER = "postgres.sbunvfcoqpecuahweiik"
DB_PASSWORD = "goQqob-rygxof-hundu4"
DB_HOST = "aws-0-eu-central-2.pooler.supabase.com"
DB_PORT = "6543"
DB_NAME = "postgres"

# Initialize connection_pool globally
connection_pool = None

def initialize_connection_pool(minconn=1, maxconn=10):
    """Initialize the connection pool."""
    global connection_pool
    try:
        if connection_pool is None:
            connection_pool = psycopg2.pool.SimpleConnectionPool(
                minconn, maxconn,  # Min and max connections in the pool
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME
            )
            if connection_pool:
                print("Connection pool created successfully")
    except Exception as e:
        print(f"Error occurred during pool initialization: {e}")

def get_connection():
    """Get a connection from the pool."""
    try:
        if connection_pool is None:
            initialize_connection_pool()  # Initialize if not already done
        return connection_pool.getconn()
    except Exception as e:
        print(f"Error occurred while getting connection: {e}")
        return None

def release_connection(conn):
    """Release a connection back to the pool."""
    try:
        if connection_pool and conn:
            connection_pool.putconn(conn)
    except Exception as e:
        print(f"Error occurred while releasing connection: {e}")

def close_connection_pool():
    """Close the connection pool."""
    try:
        if connection_pool:
            connection_pool.closeall()
            print("Connection pool closed")
    except Exception as e:
        print(f"Error occurred while closing connection pool: {e}")



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


def get_service_id(service_names):
    """
    Fetch the service IDs for a list of service names.

    Parameters:
    - service_names (list): A list of service names (e.g., ["Koko paketti", "Perus hiustenleikkuu"]).

    Returns:
    - list: A list of service IDs corresponding to the service names. 
            If a service is not found, it will be excluded from the list.
    """
    conn = get_connection()
    if not conn:
        print("Failed to connect to the database")
        return None
    
    try:
        cur = conn.cursor()
        # Convert the list of service names into a tuple for the SQL IN clause
        service_names_tuple = tuple(service_names)

        # Query to get the service IDs based on the service names
        cur.execute("""
            SELECT service_id FROM Services
            WHERE service_name IN %s
        """, (service_names_tuple,))  # Using IN clause for multiple service names

        results = cur.fetchall()
        cur.close()

        # Extract service IDs from the results
        service_ids = [result[0] for result in results]  # Create a list of service IDs

        return service_ids

    except Exception as e:
        print(f"Error occurred while fetching the service IDs: {e}")
        return None

    finally:
        # Release the connection back to the pool
        release_connection(conn)
from datetime import datetime

def fetch_barber_data_from_db(service_ids=None):
    """
    Fetch barber schedules, availability dates, existing bookings, exceptions, and service prices from the database.
    
    Parameters:
    - service_ids (list, optional): A list of service IDs to fetch prices for.
    
    Returns:
    - barber_schedules (dict): Barber IDs mapped to their working hours.
    - barber_dates (dict): Barber IDs mapped to their availability date ranges.
    - existing_bookings (dict): Barber IDs mapped to their existing bookings with total estimated time.
    - exceptions (dict): Barber-specific exceptions for custom working hours or days off.
    - barber_prices (dict): Barber IDs mapped to the total price of the specified services.
    """
    conn = get_connection() 
    if not conn:
        print("Failed to connect to the database")
        return None, None, None, None, None
    
    try:
        cur = conn.cursor()

        # Fetch barber schedules
        cur.execute("SELECT barber_id, start_time, end_time FROM BarberSchedules")
        barber_schedules = {row[0]: (row[1].strftime('%H:%M'), row[2].strftime('%H:%M')) for row in cur.fetchall()}

        # Fetch barber availability dates
        cur.execute("SELECT barber_id, start_date, end_date FROM BarberAvailability")
        barber_dates = {row[0]: (row[1], row[2]) for row in cur.fetchall()}

        # Get today's date
        today = datetime.now().date()

        # Fetch existing bookings for today and calculate total estimated time for the given services
        existing_bookings = {}
        cur.execute("""
            SELECT 
                b.barber_id, 
                b.appointment_time, 
                s.estimated_time AS main_estimated_time,
                COALESCE(SUM(EXTRACT(EPOCH FROM es.estimated_time) / 60), 0) AS total_extra_estimated_time
            FROM 
                Bookings b
            JOIN 
                Services s ON b.service_id = s.service_id
            LEFT JOIN 
                LATERAL UNNEST(b.extra) AS extra_service_id ON TRUE
            LEFT JOIN 
                Services es ON es.service_id = extra_service_id
            WHERE 
                DATE(b.appointment_time) = %s
            GROUP BY 
                b.barber_id, b.appointment_time, s.estimated_time
        """, (today,))

        for row in cur.fetchall():
            barber_id, appointment_time, main_estimated_time, total_extra_estimated_time = row
            
            # Convert main_estimated_time to total minutes
            main_estimated_minutes = main_estimated_time.total_seconds() / 60 if main_estimated_time else 0
            total_extra_estimated_time_float = float(total_extra_estimated_time)  # Convert to float

            # Sum the estimated times
            total_estimated_time = main_estimated_minutes + total_extra_estimated_time_float

            if barber_id not in existing_bookings:
                existing_bookings[barber_id] = []
            existing_bookings[barber_id].append((appointment_time.strftime('%Y-%m-%d %H:%M:%S'), total_estimated_time))

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

        # Fetch barber service prices for the given list of service_ids and sum the prices
        barber_prices = {}
        if service_ids is not None and len(service_ids) > 0:
            service_ids_tuple = tuple(service_ids)  # Convert list to tuple for SQL IN clause
            cur.execute(f"""
                SELECT barber_id, SUM(price) AS total_price
                FROM BarberServicePrices 
                WHERE service_id IN %s
                GROUP BY barber_id
            """, (service_ids_tuple,))
            barber_prices = {row[0]: float(row[1]) for row in cur.fetchall()}

        cur.close()
        return barber_schedules, barber_dates, existing_bookings, exceptions, barber_prices

    except Exception as e:
        print(f"Error occurred while fetching barber data: {e}")
        return None, None, None, None, None

    finally:
        # Release the connection back to the pool
        release_connection(conn)





def fetch_categories_and_services():
    """
    Fetch all categories and their corresponding services, including the estimated time and prices for each barber, from the database.

    Returns:
    - A dictionary where each key is a category name, and the value is a list of services for that category.
    - Each service includes its ID, name, description, estimated time in minutes, and a list of barbers with their respective prices.
    - Returns None if an error occurs.
    """
    conn = get_connection()
    if not conn:
        print("Failed to connect to the database")
        return None

    try:
        cursor = conn.cursor()

        # Updated SQL query to fetch categories, services, and barber prices
        query = """
            SELECT c.category_name, s.service_id, s.service_name, s.description, s.estimated_time,
                   b.barber_id, b.name AS barber_name, s.price
            FROM Categories c
            JOIN Services s ON c.category_id = s.category_id
            JOIN BarberServicePrices bsp ON s.service_id = bsp.service_id
            JOIN Barbers b ON bsp.barber_id = b.barber_id
            ORDER BY c.category_name, s.service_name, b.name;
        """
        cursor.execute(query)

        # Fetch results
        results = cursor.fetchall()

        # Organize results into a dictionary
        categories_services = {}
        for category_name, service_id, service_name, description, estimated_time, barber_id, barber_name, price in results:
            if category_name not in categories_services:
                categories_services[category_name] = []

            # Find or create the service entry in the list
            service_entry = next((s for s in categories_services[category_name] if s['service_id'] == service_id), None)
            if not service_entry:
                # Convert estimated_time (assumed to be a timedelta) to minutes
                estimated_time_minutes = None
                if isinstance(estimated_time, timedelta):
                    estimated_time_minutes = int(estimated_time.total_seconds() / 60)

                service_entry = {
                    "service_id": service_id,
                    "service_name": service_name,
                    "description": description,
                    "estimated_time": estimated_time_minutes,  # Store time in minutes
                    "price": price  # List to hold barber details
                }
                categories_services[category_name].append(service_entry)



        # Close the cursor and release the connection
        cursor.close()
        release_connection(conn)
        print("Connection released successfully.")
        
        return categories_services

    except Exception as e:
        print(f"Error occurred while fetching categories and services: {e}")
        traceback.print_exc()
        release_connection(conn)
        return None


from datetime import datetime
import traceback

def insert_booking(barber_id, service_id, customer_name, appointment_time, email, phone, price, extra):
    """
    Insert a new booking into the Bookings table.

    Parameters:
    - barber_id (int): The ID of the barber.
    - service_id (int): The ID of the service.
    - customer_name (str): The name of the customer.
    - appointment_time (datetime): The appointment time.
    - email (str): The email address of the customer.
    - phone (str): The phone number of the customer.

    Returns:
    - A tuple (success, message), where success is a boolean indicating if the booking was inserted,
      and message is a string indicating the result.
    """
    conn = get_connection()
    if not conn:
        print("Failed to connect to the database")
        return False, "Failed to connect to the database."

    try:
        cursor = conn.cursor()

        # Check if there is an existing booking for the barber at the same time
        check_query = """
            SELECT COUNT(*) FROM Bookings
            WHERE barber_id = %s AND appointment_time = %s;
        """
        cursor.execute(check_query, (barber_id, appointment_time))
        (existing_bookings,) = cursor.fetchone()

        if existing_bookings > 0:
            print(f"Barber {barber_id} is already booked at {appointment_time}.")
            cursor.close()
            release_connection(conn)
            return False, "Time slot unavailable. Choose another time."

        # SQL query to insert a new booking
        insert_query = """
            INSERT INTO Bookings (barber_id, service_id, customer_name, appointment_time, email, phone, price, extra)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        # Execute the query with provided data
        cursor.execute(insert_query, (barber_id, service_id, customer_name, appointment_time, email, phone, price, extra))
        
        # Commit the transaction
        conn.commit()
        print("Booking inserted successfully.")

        # Close the cursor and release the connection
        cursor.close()
        release_connection(conn)
        print("Connection released successfully.")
        
        return True, "Booking created successfully."

    except Exception as e:
        print(f"Error occurred while inserting booking: {e}")
        traceback.print_exc()
        release_connection(conn)
        return False, "An error occurred while creating the booking."


def update_booking_price(booking_id, new_price):
    """
    Update the price of a booking in the Bookings table.

    Parameters:
    - booking_id (int): The ID of the booking to be updated.
    - new_price (float): The new price to set for the booking.

    Returns:
    - A tuple (success, message), where success is a boolean indicating if the price was updated,
      and message is a string indicating the result.
    """
    conn = get_connection()
    if not conn:
        print("Failed to connect to the database")
        return False, "Failed to connect to the database."

    try:
        cursor = conn.cursor()

        # Check if the booking exists
        check_query = """
            SELECT COUNT(*) FROM Bookings WHERE booking_id = %s;
        """
        cursor.execute(check_query, (booking_id,))
        (booking_exists,) = cursor.fetchone()

        if booking_exists == 0:
            print(f"Booking ID {booking_id} does not exist.")
            cursor.close()
            release_connection(conn)
            return False, "Booking ID does not exist."

        # SQL query to update the price for the booking
        update_query = """
            UPDATE Bookings
            SET price = %s
            WHERE booking_id = %s;
        """
        # Execute the query with the new price and booking ID
        cursor.execute(update_query, (new_price, booking_id))

        # Commit the transaction
        conn.commit()
        print(f"Price updated successfully for booking ID {booking_id}.")

        # Close the cursor and release the connection
        cursor.close()
        release_connection(conn)
        print("Connection released successfully.")
        
        return True, "Booking price updated successfully."

    except Exception as e:
        print(f"Error occurred while updating booking price: {e}")
        traceback.print_exc()
        release_connection(conn)
        return False, "An error occurred while updating the booking price."

import traceback  # Ensure traceback is imported
from datetime import timedelta

def convert_timedelta_to_minutes(td):
    """Converts a timedelta object to total minutes."""
    if isinstance(td, timedelta):
        total_minutes = int(td.total_seconds() // 60)
        return total_minutes
    return td  # If not a timedelta, return as is

from datetime import datetime, timedelta
import traceback

def convert_timedelta_to_minutes(td):
    """Convert timedelta or string representation of time to total minutes."""
    if isinstance(td, str):
        # If td is a string, convert it to a timedelta
        hours, minutes, seconds = map(int, td.split(':'))
        td = timedelta(hours=hours, minutes=minutes, seconds=seconds)
    elif td is None:
        return 0  # Handle None values
    elif not isinstance(td, timedelta):
        raise ValueError("Unsupported type for duration.")

    return int(td.total_seconds() // 60)  # Convert seconds to minutes
def get_bookings_from_today_onwards(barber_id):
    """
    Retrieve all columns from the Bookings table for a specific barber ID from today's date and onwards,
    including service name, extra fields, extra service names, and estimated time in minutes.

    Parameters:
    - barber_id (int): The ID of the barber.

    Returns:
    - A tuple (success, result), where success is a boolean indicating if the operation was successful,
      and result is either a list of bookings or an error message.
    """
    conn = get_connection()
    if not conn:
        print("Failed to connect to the database")
        return False, "Failed to connect to the database."

    try:
        cursor = conn.cursor()

        # SQL query to get all bookings for the barber from today's date and onwards
        today_date = datetime.now().date()
        query = """
            SELECT 
                B.booking_id, 
                B.barber_id, 
                B.service_id, 
                S.service_name AS main_service_name,  -- Main service name
                B.customer_name, 
                B.appointment_time, 
                B.email, 
                B.phone, 
                B.price, 
                S.estimated_time AS estimated_time,  -- Assuming 'estimated_time' is the correct column name
                ARRAY(
                    SELECT json_build_object(
                        'service_name', E.service_name,
                        'duration', E.estimated_time
                    )
                    FROM Services E
                    WHERE E.service_id = ANY(B.extra)
                ) AS extra_services  -- Fetch the names of extra services as a JSON object
            FROM 
                Bookings B
            JOIN 
                Services S ON B.service_id = S.service_id  -- Join for main service name and duration
            WHERE 
                B.barber_id = %s 
                AND DATE(B.appointment_time) >= %s  -- Retrieve bookings from today onwards
            ORDER BY 
                B.appointment_time ASC;  -- Order by appointment time ascending
        """
        
        # Execute the query
        cursor.execute(query, (barber_id, today_date))
        bookings = cursor.fetchall()

        # Format the bookings as a list of dictionaries
        formatted_bookings = []
        for booking in bookings:
            # Get the main service estimated time in minutes
            main_service_time = convert_timedelta_to_minutes(booking[9])

            # Prepare extra services with their names only
            extra_services = [
                extra_service['service_name']
                for extra_service in booking[10]  # booking[10] contains the array of extra services
            ]

            # Calculate total estimated time including extra services
            total_estimated_time = main_service_time + sum(
                convert_timedelta_to_minutes(extra_service['duration']) for extra_service in booking[10]
            )

            # Build the formatted booking dictionary including extra services
            formatted_bookings.append({
                'booking_id': booking[0],
                'service_name': booking[3],       # Include main service name
                'customer_name': booking[4],
                'appointment_time': booking[5].strftime('%Y-%m-%d %H:%M:%S'),  # Format appointment time
                'email': booking[6],
                'phone': booking[7],
                'price': booking[8],
                'total_estimated_time': total_estimated_time,  # Total estimated time
                'extra_services': extra_services  # Include only service names of extra services
            })

        # Close the cursor and release the connection
        cursor.close()
        release_connection(conn)

        if bookings:
            return True, formatted_bookings
        else:
            return True, "No bookings found from today onwards."

    except Exception as e:
        print(f"Error occurred while retrieving bookings: {e}")
        traceback.print_exc()  # This will print the full traceback in the console
        release_connection(conn)
        return False, "An error occurred while fetching bookings."

def insert_barber_break_slot(barber_id, break_date, break_times, timeType, booking_id=None):
    """
    Insert multiple break time slots into the BarberBreaks table.

    Parameters:
    - barber_id (int): The ID of the barber.
    - break_date (date): The date of the break.
    - break_times (list of time): A list of specific time slots for the break.
    - booking_id (int or None): The ID of the booking associated with the break, or None if not applicable.

    Returns:
    - bool: True if the insertion is successful for all times, False otherwise.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO BarberBreaks (barber_id, break_date, break_time, type , booking_id)
            VALUES (%s, %s, %s, %s, %s)
        """

        # Loop through each time in the array and insert into the database
        for break_time in break_times:
            cursor.execute(query, (barber_id, break_date, break_time, timeType, booking_id))

        # Commit the transaction if all insertions are successful
        conn.commit()
        cursor.close()
        release_connection(conn)
        return True  # Indicate success
    except Exception as e:
        # Rollback the transaction in case of any error
        if conn:
            conn.rollback()
        release_connection(conn)
        print(f"Error inserting barber breaks: {e}")
        return False  # Indicate failure

def delete_barber_break(break_id):
    """
    Delete a break slot from the BarberBreaks table based on break_id.

    Parameters:
    - break_id (int): The ID of the break to delete.

    Returns:
    - bool: True if the deletion is successful, False otherwise.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        query = """
            DELETE FROM BarberBreaks WHERE break_id = %s
        """
        cursor.execute(query, (break_id,))
        conn.commit()
        cursor.close()
        release_connection(conn)
        return True  # Indicate success
    except Exception as e:
        release_connection(conn)
        print(f"Error deleting barber break: {e}")
        return False  # Indicate failure

from datetime import datetime, timedelta

def round_up_to_next_15_minutes(dt):
    """
    Round a datetime object up to the next 15-minute interval.
    """
    if dt.minute % 15 == 0:
        return dt
    else:
        return dt + timedelta(minutes=(15 - dt.minute % 15))

import datetime
from datetime import timedelta, datetime

def round_up_to_next_15_minutes(dt):
    """
    Rounds the time to the next 15-minute interval.
    """
    discard = timedelta(minutes=dt.minute % 15, seconds=dt.second, microseconds=dt.microsecond)
    return dt + (timedelta(minutes=15) - discard)

def get_available_free_slots(barber_id, date):
    """
    Fetch available free time slots for a barber on a specific date, considering
    service arrays in bookings (both main and extra services).

    Parameters:
    - barber_id (int): The ID of the barber.
    - date (datetime.date or str): The date for which to check availability.

    Returns:
    - List of available time slots in "HH:MM" format.
    """
    # Ensure that date is a datetime.date object
    if isinstance(date, str):
        try:
            date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError as e:
            print(f"Error parsing date: {e}")
            return []

    # Get the current time
    now = datetime.now()

    conn = get_connection()
    if not conn:
        print("Failed to connect to the database")
        return []

    try:
        cursor = conn.cursor()

        # 1. Fetch the barber's working hours from BarberSchedules
        cursor.execute("""
            SELECT start_time, end_time 
            FROM BarberSchedules 
            WHERE barber_id = %s
        """, (barber_id,))
        schedule = cursor.fetchone()

        if not schedule:
            print(f"No schedule found for barber ID {barber_id}")
            return []

        start_time, end_time = schedule
        start_time = datetime.combine(date, start_time)
        end_time = datetime.combine(date, end_time)

        # If the date is today, adjust the start time to be at least the current time
        if date == now.date() and start_time < now:
            start_time = now

        # Round start_time to the next nearest 15-minute interval
        start_time = round_up_to_next_15_minutes(start_time)

        # 2. Fetch barber's breaks for the specific date
        cursor.execute("""
            SELECT break_time 
            FROM BarberBreaks
            WHERE barber_id = %s AND break_date = %s
        """, (barber_id, date))
        breaks = cursor.fetchall()

        # Convert the fetched break times into datetime objects
        break_times = [datetime.combine(date, break_time[0]) for break_time in breaks]

        # 3. Fetch existing bookings for the barber on the specified date, including extra services
        cursor.execute("""
            SELECT appointment_time, s.estimated_time, b.extra
            FROM Bookings b
            JOIN Services s ON b.service_id = s.service_id
            WHERE b.barber_id = %s AND DATE(b.appointment_time) = %s
        """, (barber_id, date))
        bookings = cursor.fetchall()

        booked_slots = []
        for appointment_time, estimated_time, extra_services in bookings:
            booking_start = appointment_time
            total_estimated_time = estimated_time

            # If there are extra services, fetch their estimated times and add them
            if extra_services:
                extra_service_ids = tuple(extra_services)  # assuming extra_services is an array of service IDs
                if extra_service_ids:  # ensure extra_service_ids is not empty
                    cursor.execute("""
                        SELECT estimated_time
                        FROM Services
                        WHERE service_id IN %s
                    """, (extra_service_ids,))
                    extra_times = cursor.fetchall()

                    # Add the estimated times of all extra services
                    for extra_time in extra_times:
                        total_estimated_time += extra_time[0]  # Assuming extra_time is a timedelta

            booking_end = booking_start + total_estimated_time
            booked_slots.append((booking_start, booking_end))

        # 4. Generate time slots in increments (e.g., every 15 minutes)
        current_time = start_time
        available_slots = []

        # Adjust the condition to ensure the last slot is included
        while current_time < end_time:
            slot_end_time = current_time + timedelta(minutes=15)

            # Debugging: print the current slot being checked
            print(f"Checking slot: {current_time.strftime('%H:%M')} - {slot_end_time.strftime('%H:%M')}")

            # Check if the time slot overlaps with any booked slots
            overlap = False
            for booking_start, booking_end in booked_slots:
                print(f"Comparing with booking: {booking_start.strftime('%H:%M')} - {booking_end.strftime('%H:%M')}")
                if (current_time < booking_end) and (slot_end_time > booking_start):
                    print(f"Overlap with booking {booking_start.strftime('%H:%M')} - {booking_end.strftime('%H:%M')}")
                    overlap = True
                    break

            # Check if the time slot overlaps with any break slots
            for break_time in break_times:
                print(f"Comparing with break: {break_time.strftime('%H:%M')}")
                if (current_time <= break_time < slot_end_time) or (break_time <= current_time < break_time + timedelta(minutes=15)):
                    print(f"Overlap with break at {break_time.strftime('%H:%M')}")
                    overlap = True
                    break

            # Only add slots that are in the future (from the current time onwards) and have no overlaps
            if not overlap and current_time >= now:
                available_slots.append(current_time.strftime('%H:%M'))

            current_time += timedelta(minutes=15)

        # Close the cursor and connection
        cursor.close()
        release_connection(conn)

        return available_slots

    except Exception as e:
        print(f"Error occurred while fetching available slots: {e}")
        if conn:
            release_connection(conn)
        return []






def get_bookings_for_barber(barber_id, date):
    """
    Fetch bookings for a specific barber on a given date.
    
    Parameters:
    - barber_id (int): The ID of the barber.
    - date (datetime.date): The date for which to fetch bookings.
    
    Returns:
    - List of dictionaries containing appointment time and service duration (in minutes).
    """
    conn = get_connection()
    if not conn:
        print("Failed to connect to the database")
        return []

    try:
        cursor = conn.cursor()

        # SQL query to get all bookings for the barber on the specified date
        query = """
            SELECT appointment_time, s.estimated_time 
            FROM Bookings b
            JOIN Services s ON b.service_id = s.service_id
            WHERE b.barber_id = %s AND DATE(b.appointment_time) = %s
        """
        cursor.execute(query, (barber_id, date))

        bookings = []
        for row in cursor.fetchall():
            appointment_time, estimated_time = row
            # Convert estimated time to minutes if it's a timedelta
            if isinstance(estimated_time, timedelta):
                estimated_time_minutes = int(estimated_time.total_seconds() / 60)
            else:
                estimated_time_minutes = estimated_time

            bookings.append({
                "appointment_time": appointment_time,
                "service_duration": estimated_time_minutes  # Store duration in minutes
            })

        cursor.close()
        release_connection(conn)
        return bookings

    except Exception as e:
        print(f"Error occurred while fetching bookings for barber {barber_id}: {e}")
        release_connection(conn)
        return []


def get_existing_breaks_for_barber(barber_id, break_date):
    """
    Fetch all existing break slots for a barber on a given date.
    
    Parameters:
    - barber_id (int): The ID of the barber.
    - break_date (datetime.date): The date to fetch the breaks for.
    
    Returns:
    - List of break times in 'HH:MM' format for the barber on the given date.
    """
    conn = get_connection()
    if not conn:
        print("Failed to connect to the database")
        return []

    try:
        cursor = conn.cursor()

        # SQL query to get all break times for the barber on the specified date
        query = """
            SELECT break_time 
            FROM BarberBreaks
            WHERE barber_id = %s AND break_date = %s
        """
        cursor.execute(query, (barber_id, break_date))
        existing_breaks = cursor.fetchall()
        
        # Ensure you're seeing all breaks properly
        print(f"Raw fetched breaks for barber {barber_id} on {break_date}: {existing_breaks}")

        # Check if multiple entries are being fetched or not
        if len(existing_breaks) < 2:
            print("Only one or no break times found, this may be the issue!")

        # Convert the fetched results to a list of formatted break times
        breaks = [row[0].strftime('%H:%M') for row in existing_breaks]

        # Print formatted times
        print(f"Formatted break times: {breaks}")

        cursor.close()
        release_connection(conn)
        return breaks

    except Exception as e:
        print(f"Error occurred while fetching breaks for barber {barber_id} on {break_date}: {e}")
        release_connection(conn)
        return []



def hash_password(password):
    salt = os.urandom(16)  # Generate a new salt
    # Hash the password using the salt
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return salt, password_hash

def barber_exists(barber_id):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute('SELECT * FROM barber_login WHERE barber_id = %s', (barber_id,))
        count = cur.fetchone()[0]
        return count > 0  # Returns True if exists, False otherwise
    finally:
        cur.close()
        conn.close()


def create_user(barber_id, username, password):
    if barber_exists(barber_id):
        return "barber_exists"  # Barber ID already exists

    conn = get_connection()
    cur = conn.cursor()

    try:
        salt, password_hash = hash_password(password)
        cur.execute('INSERT INTO barber_login (barber_id, username, password_hash, salt) VALUES (%s, %s, %s, %s)',
                    (barber_id, username, password_hash, salt))
        conn.commit()
        return "success"  # User created successfully
    except psycopg2.IntegrityError:
        conn.rollback()
        return "username_exists"  # Username already exists
    finally:
        cur.close()
        conn.close()



def verify_user(username, password):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute('SELECT password_hash, salt, barber_id FROM barber_login WHERE username = %s', (username,))
        result = cur.fetchone()

        if result is None:
            return "user_not_found", None  # Username does not exist

        password_hash, salt, barber_id = result

        if isinstance(password_hash, memoryview):
            password_hash = bytes(password_hash)
        if isinstance(salt, memoryview):
            salt = bytes(salt)

        provided_password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)

        if provided_password_hash == password_hash:
            return "login_success", barber_id  # Return barber_id on success
        else:
            return "invalid_password", None  # Incorrect password
    finally:
        cur.close()
        conn.close()


from datetime import datetime
def get_barber_breaks(barber_id, break_type=None):
    """
    Retrieve all columns from the BarberBreaks table for a specific barber ID,
    returning only breaks from today's date onward. If break_type is provided,
    it will filter by the break type.
    
    Parameters:
    - barber_id (int): The ID of the barber.
    - break_type (str or None): The type of break to filter by (e.g., "Extend", "Break").
    
    Returns:
    - tuple (bool, result): Success status and list of breaks or error message.
    """
    conn = get_connection()
    if not conn:
        print("Failed to connect to the database")
        return False, "Failed to connect to the database."

    try:
        cursor = conn.cursor()
        
        # Get today's date
        today = datetime.now().date()
        
        # Query to select breaks from today onward, with optional filtering by type
        if break_type:
            query = """
            SELECT * FROM BarberBreaks 
            WHERE barber_id = %s AND break_date >= %s AND type = %s;
            """
            cursor.execute(query, (barber_id, today, break_type))
        else:
            query = """
            SELECT * FROM BarberBreaks 
            WHERE barber_id = %s AND break_date >= %s;
            """
            cursor.execute(query, (barber_id, today))

        breaks = cursor.fetchall()

        formatted_breaks = []
        if breaks:
            for break_ in breaks:
                # Fetch the break_date and break_time
                break_id = break_[0]
                barber_id = break_[1]
                break_date = break_[2]  # This should be a date object
                break_time = break_[3]   # This should be a time object
                type_ = break_[4]        # The break type (Extend, Break, etc.)
                booking_id = break_[5]        # The break type (Extend, Break, etc.)

                
                # # Debug: Print the values before formatting
                # print(f"Break ID: {break_id}, Barber ID: {barber_id}, Break Date: {break_date}, Break Time: {break_time}, Type: {type_}")
                
                # Format break_time and break_date
                formatted_breaks.append({
                    'break_id': break_id,
                    'booking_id': booking_id,

                    'barber_id': barber_id,
                    'break_time': break_time.strftime('%H:%M:%S') if break_time else "N/A",
                    'break_date': break_date.strftime('%d.%m.%Y') if break_date else "N/A",
                    'type': type_ if type_ else "N/A"  # Include the break type
                })

        cursor.close()
        release_connection(conn)

        return True, formatted_breaks if formatted_breaks else "No future breaks found for this barber."

    except Exception as e:
        print(f"Error occurred while retrieving breaks: {e}")
        traceback.print_exc()
        release_connection(conn)
        return False, "An error occurred while fetching breaks."


def get_barber_name_by_id(barber_id):
    """
    Fetch the barber's name from the barbers table using the barber_id.

    Parameters:
    - barber_id (int): The ID of the barber.

    Returns:
    - str: The name of the barber, or None if no barber is found.
    """
    conn = get_connection()
    if not conn:
        print("Failed to connect to the database")
        return None
    
    try:
        cur = conn.cursor()

        # Query to get the barber's name by barber_id
        cur.execute("""
            SELECT name FROM barbers
            WHERE barber_id = %s
        """, (barber_id,))  # Safely passing barber_id as a parameter to avoid SQL injection

        result = cur.fetchone()
        cur.close()

        if result:
            return result[0]  # Return the barber's name
        else:
            return None  # Return None if no barber was found

    except Exception as e:
        print(f"Error occurred while fetching the barber's name: {e}")
        return None

    finally:
        # Release the connection back to the pool
        release_connection(conn)



def get_barber_schedule(barber_id):
    """
    Fetch the start and end times for a barber based on barber_id.

    Parameters:
    - barber_id (int): The ID of the barber.

    Returns:
    - tuple: A tuple containing the start_time and end_time, or None if not found.
    """
    conn = get_connection()
    if not conn:
        print("Failed to connect to the database")
        return None

    try:
        cur = conn.cursor()

        # SQL query to get the start and end times from BarberSchedules
        cur.execute("""
            SELECT start_time, end_time 
            FROM BarberSchedules 
            WHERE barber_id = %s
        """, (barber_id,))

        # Fetch the result
        result = cur.fetchone()
        cur.close()

        if result:
            return result  # Return tuple (start_time, end_time)
        else:
            return None  # No schedule found for the barber

    except Exception as e:
        print(f"Error occurred while fetching the barber schedule: {e}")
        return None

    finally:
        release_connection(conn)


def update_barber_schedule(barber_id, start_time, end_time):
    """
    Update the start and end times for a barber based on barber_id.

    Parameters:
    - barber_id (int): The ID of the barber.
    - start_time (str): The new start time (in 'HH:MM:SS' format).
    - end_time (str): The new end time (in 'HH:MM:SS' format).

    Returns:
    - bool: True if the update was successful, False otherwise.
    """
    conn = get_connection()
    if not conn:
        print("Failed to connect to the database")
        return False

    try:
        cur = conn.cursor()

        # SQL query to update the start and end times
        cur.execute("""
            UPDATE BarberSchedules
            SET start_time = %s, end_time = %s
            WHERE barber_id = %s
        """, (start_time, end_time, barber_id))

        # Commit the transaction to apply the changes
        conn.commit()

        cur.close()
        return True  # Return True if the update was successful

    except Exception as e:
        print(f"Error occurred while updating the barber schedule: {e}")
        return False

    finally:
        release_connection(conn)


from datetime import datetime

def get_barber_exceptions(barber_id):
    """
    Fetch all future barber exceptions starting from the current day.

    Parameters:
    - barber_id (int): The ID of the barber.

    Returns:
    - list: A list of dictionaries representing the rows fetched from BarberExceptions.
    """
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cur = conn.cursor()

        # SQL query to get future barber exceptions
        cur.execute("""
            SELECT barber_id, exception_date, custom_start_time, custom_end_time, is_off
            FROM BarberExceptions
            WHERE barber_id = %s AND exception_date >= CURRENT_DATE
            ORDER BY exception_date ASC
        """, (barber_id,))

        # Fetch all the rows
        results = cur.fetchall()
        cur.close()

        # Format the results into a list of dictionaries for JSON serialization
        exceptions = []
        for result in results:
            exceptions.append({
                "barber_id": result[0],
                "exception_date": result[1].strftime("%Y-%m-%d"),  # Convert date to string
                "custom_start_time": result[2].strftime("%H:%M:%S") if result[2] else None,  # Convert time to string
                "custom_end_time": result[3].strftime("%H:%M:%S") if result[3] else None,  # Convert time to string
                "is_off": result[4]
            })

        return exceptions  # Return the list of formatted exceptions

    except Exception as e:
        print(f"Error occurred while fetching barber exceptions: {e}")
        return None

    finally:
        release_connection(conn)

def insert_barber_exception(barber_id, exception_date, custom_start_time=None, custom_end_time=None, is_off=False):
    """
    Insert a new record into the BarberExceptions table for a specific barber.

    Parameters:
    - barber_id (int): The ID of the barber.
    - exception_date (str): The date of the exception (format: 'YYYY-MM-DD').
    - custom_start_time (str or None): The custom start time for that date (format: 'HH:MM:SS'). None if it's a day off.
    - custom_end_time (str or None): The custom end time for that date (format: 'HH:MM:SS'). None if it's a day off.
    - is_off (bool): Whether the barber is off on that date (True for day off, False for custom hours).

    Returns:
    - bool: True if the insert was successful, False otherwise.
    """
    conn = get_connection()
    if not conn:
        return False

    try:
        cur = conn.cursor()

        # SQL query to insert a new record into the BarberExceptions table
        cur.execute("""
            INSERT INTO BarberExceptions (barber_id, exception_date, custom_start_time, custom_end_time, is_off)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (barber_id, exception_date)
            DO UPDATE SET custom_start_time = EXCLUDED.custom_start_time,
                          custom_end_time = EXCLUDED.custom_end_time,
                          is_off = EXCLUDED.is_off
        """, (barber_id, exception_date, custom_start_time, custom_end_time, is_off))

        # Commit the transaction to apply the changes
        conn.commit()

        cur.close()
        return True  # Return True if the insert was successful

    except Exception as e:
        print(f"Error occurred while inserting barber exception: {e}")
        return False

    finally:
        release_connection(conn)





def get_barber_data(barber_id):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Query to fetch all data from bookings, barberbreaks, and barberexceptions based on barber_id
        query = """
        SELECT 
            b.booking_id, b.barber_id, b.service_id, b.customer_name, b.appointment_time, 
            b.email, b.phone, b.price, b.extra_charge, b.extra,
            br.break_id, br.break_date, br.break_time, br.type, br.booking_id AS break_booking_id,
            be.exception_date, be.custom_start_time, be.custom_end_time, be.is_off
        FROM 
            bookings b
        LEFT JOIN 
            barberbreaks br ON b.barber_id = br.barber_id
        LEFT JOIN 
            barberexceptions be ON b.barber_id = be.barber_id
        WHERE 
            b.barber_id = %s;
        """
        cursor.execute(query, (barber_id,))
        results = cursor.fetchall()

        # Fetch column names for readability
        colnames = [desc[0] for desc in cursor.description]
        
        # Formatting the result
        data = [dict(zip(colnames, row)) for row in results]

        return data
    
    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        if conn:
            cursor.close()
            conn.close()
from datetime import timedelta

def get_appointments_and_breaks(barber_id, selected_date):
    """
    Fetch appointment times from the bookings table, break date/time and type from the barberbreaks table,
    start/end time from the BarberSchedules table, and exception times from BarberExceptions.

    Parameters:
    - barber_id (int): The ID of the barber.
    - selected_date (datetime.date): The date for which to fetch appointments.
    
    Returns:
    - List of dictionaries containing separate date and time for appointments, breaks (as a list),
      the final start_time and end_time, and calculated appointment end time.
    """
    conn = get_connection()  # Assuming you have a function to get the database connection
    if not conn:
        print("Failed to connect to the database")
        return []

    try:
        cursor = conn.cursor()

        # SQL query to fetch appointments, breaks, schedules, exceptions, and services
        query = """
            SELECT 
                b.appointment_time, 
                b.service_id,
                b.extra,
                bb.break_date, 
                bb.break_time,
                bb.type AS break_type,
                bs.start_time, 
                bs.end_time,
                be.exception_date, 
                be.custom_start_time, 
                be.custom_end_time, 
                be.is_off,
                s.estimated_time AS primary_estimated_time
            FROM 
                bookings b
            LEFT JOIN 
                barberbreaks bb ON b.barber_id = bb.barber_id
            JOIN 
                BarberSchedules bs ON b.barber_id = bs.barber_id
            LEFT JOIN 
                BarberExceptions be ON b.barber_id = be.barber_id AND DATE(b.appointment_time) = be.exception_date
            JOIN 
                Services s ON b.service_id = s.service_id
            WHERE 
                b.barber_id = %s AND DATE(b.appointment_time) = %s;
        """
        cursor.execute(query, (barber_id, selected_date))
        results = cursor.fetchall()

        appointments_dict = {}

        # Loop through the query result
        for row in results:
            appointment_time, service_id, extra, break_date, break_time, break_type, start_time, end_time, exception_date, custom_start_time, custom_end_time, is_off, primary_estimated_time = row

            # Ensure primary_estimated_time is an integer representing minutes
            if isinstance(primary_estimated_time, timedelta):
                primary_estimated_time = int(primary_estimated_time.total_seconds() // 60)

            # Format the final start and end time based on the exception or regular schedule
            if exception_date and not is_off:
                final_start_time = custom_start_time.strftime('%H:%M:%S') if custom_start_time else start_time.strftime('%H:%M:%S')
                final_end_time = custom_end_time.strftime('%H:%M:%S') if custom_end_time else end_time.strftime('%H:%M:%S')
            else:
                final_start_time = start_time.strftime('%H:%M:%S')
                final_end_time = end_time.strftime('%H:%M:%S')

            # Split the appointment_time into date and time
            appointment_date = appointment_time.strftime('%Y-%m-%d')
            appointment_only_time = appointment_time.strftime('%H:%M:%S')

            # Calculate the total estimated time
            total_estimated_time = primary_estimated_time  # Start with the primary service time

            # If there are extra services, calculate the estimated time for each
            if extra and isinstance(extra, list):  # Check if 'extra' is a list
                extra_service_ids = tuple(map(int, extra))  # Convert the extra services to integers
                if extra_service_ids:
                    extra_services_query = """
                        SELECT SUM(estimated_time)
                        FROM Services
                        WHERE service_id IN %s;
                    """
                    cursor.execute(extra_services_query, (extra_service_ids,))
                    extra_estimated_time = cursor.fetchone()[0] or 0

                    # Ensure extra_estimated_time is treated as an integer
                    if isinstance(extra_estimated_time, timedelta):
                        extra_estimated_time = int(extra_estimated_time.total_seconds() // 60)

                    total_estimated_time += extra_estimated_time

            # Calculate the appointment end time by adding the total estimated time (in minutes) to the appointment start time
            appointment_end_time = appointment_time + timedelta(minutes=total_estimated_time)

            # Group the appointments by appointment_date
            if appointment_date not in appointments_dict:
                appointments_dict[appointment_date] = {
                    "date": appointment_date,
                    "appointments": []
                }

            # Check if this appointment already exists (use time as a key)
            existing_appointment = next(
                (a for a in appointments_dict[appointment_date]["appointments"] if a["appointment_time"] == appointment_only_time), None
            )

            if not existing_appointment:
                # Add this appointment to the list
                appointments_dict[appointment_date]["appointments"].append({
                    "appointment_time": appointment_only_time,
                    "appointment_end_time": appointment_end_time.strftime('%H:%M:%S'),  # Convert end time to a string
                    "breaks": [],
                    "start_time": final_start_time,
                    "end_time": final_end_time,
                    "is_off": is_off
                })
                existing_appointment = appointments_dict[appointment_date]["appointments"][-1]

            # If there's a break, append it to the current appointment's "breaks" list
            if break_date and break_time and break_type:
                existing_appointment["breaks"].append({
                    "break_date": break_date.strftime('%Y-%m-%d'),
                    "break_time": break_time.strftime('%H:%M:%S'),
                    "break_type": break_type
                })

        cursor.close()
        release_connection(conn)

        # Return the grouped appointments with date and time split, and calculated appointment end time
        return list(appointments_dict.values())

    except Exception as e:
        print(f"Error occurred while fetching data for barber {barber_id}: {e}")
        release_connection(conn)
        return []