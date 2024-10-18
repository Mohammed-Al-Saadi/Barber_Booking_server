
from datetime import timedelta
from database.database_conn import get_connection, release_connection


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

