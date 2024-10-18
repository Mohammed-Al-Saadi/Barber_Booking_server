

import traceback
from database.database_conn import get_connection, release_connection


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
