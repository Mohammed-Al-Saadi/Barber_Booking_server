

from datetime import datetime

from database.database_conn import get_connection, release_connection

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



