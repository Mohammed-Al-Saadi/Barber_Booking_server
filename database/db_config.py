# db_connection.py
import hashlib
import os
import traceback
import psycopg2
from psycopg2 import pool
from datetime import datetime, timedelta


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

data = get_barbers_for_service(service_names=["Hiustatuointi"])
print(data)

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






def insert_barber_break_slot(barber_id, break_date, break_time):
    """
    Insert a break time slot into the BarberBreaks table.

    Parameters:
    - barber_id (int): The ID of the barber.
    - break_date (date): The date of the break.
    - break_time (time): The specific time slot for the break.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO BarberBreaks (barber_id, break_date, break_time)
            VALUES (%s, %s, %s)
        """
        cursor.execute(query, (barber_id, break_date, break_time))
        conn.commit()
        cursor.close()
        release_connection(conn)
    except Exception as e:
        release_connection(conn)
        print(f"Error inserting barber break: {e}")




# def get_available_free_slots(barber_id, date):
#     """
#     Fetch available free time slots for a barber on a specific date.
    
#     Parameters:
#     - barber_id (int): The ID of the barber.
#     - date (datetime.date): The date for which to check availability.
    
#     Returns:
#     - List of available time slots in "HH:MM" format.
#     """
#     conn = get_connection()
#     if not conn:
#         print("Failed to connect to the database")
#         return []

#     try:
#         cursor = conn.cursor()

#         # 1. Fetch the barber's working hours from BarberSchedules
#         cursor.execute("""
#             SELECT start_time, end_time 
#             FROM BarberSchedules 
#             WHERE barber_id = %s
#         """, (barber_id,))
#         schedule = cursor.fetchone()

#         if not schedule:
#             print(f"No schedule found for barber ID {barber_id}")
#             return []

#         start_time, end_time = schedule
#         start_time = datetime.combine(date, start_time)
#         end_time = datetime.combine(date, end_time)

#         # 2. Fetch barber's breaks for the specific date
#         cursor.execute("""
#             SELECT break_time 
#             FROM BarberBreaks
#             WHERE barber_id = %s AND break_date = %s
#         """, (barber_id, date))
#         breaks = cursor.fetchall()

#         break_times = [datetime.combine(date, break_time[0]) for break_time in breaks]

#         # 3. Fetch existing bookings for the barber on the specified date
#         cursor.execute("""
#             SELECT appointment_time, s.estimated_time
#             FROM Bookings b
#             JOIN Services s ON b.service_id = s.service_id
#             WHERE b.barber_id = %s AND DATE(b.appointment_time) = %s
#         """, (barber_id, date))
#         bookings = cursor.fetchall()

#         booked_slots = []
#         for appointment_time, estimated_time in bookings:
#             booking_start = appointment_time
#             booking_end = booking_start + estimated_time
#             booked_slots.append((booking_start, booking_end))

#         # 4. Generate time slots in increments (e.g., every 15 minutes)
#         current_time = start_time
#         available_slots = []

#         while current_time + timedelta(minutes=15) <= end_time:
#             slot_end_time = current_time + timedelta(minutes=15)

#             # Check if the time slot overlaps with any booked slots or break slots
#             overlap = False
#             for booking_start, booking_end in booked_slots:
#                 if (current_time < booking_end) and (slot_end_time > booking_start):
#                     overlap = True
#                     break

#             if current_time in break_times:
#                 overlap = True

#             if not overlap:
#                 available_slots.append(current_time.strftime('%H:%M'))

#             current_time += timedelta(minutes=15)

#         # Close the cursor and connection
#         cursor.close()
#         release_connection(conn)

#         return available_slots

#     except Exception as e:
#         print(f"Error occurred while fetching available slots: {e}")
#         if conn:
#             release_connection(conn)
#         return []



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
