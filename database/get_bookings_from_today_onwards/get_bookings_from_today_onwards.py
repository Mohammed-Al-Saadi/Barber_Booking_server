
def convert_timedelta_to_minutes(td):
    """Converts a timedelta object to total minutes."""
    if isinstance(td, timedelta):
        total_minutes = int(td.total_seconds() // 60)
        return total_minutes
    return td  # If not a timedelta, return as is

from datetime import datetime, timedelta
import traceback

from database.database_conn import get_connection, release_connection

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
