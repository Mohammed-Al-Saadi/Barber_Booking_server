

from database.database_conn import get_connection, release_connection


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
