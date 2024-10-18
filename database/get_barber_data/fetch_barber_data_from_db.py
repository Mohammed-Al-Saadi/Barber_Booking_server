
from datetime import datetime
from database.database_conn import get_connection, release_connection


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