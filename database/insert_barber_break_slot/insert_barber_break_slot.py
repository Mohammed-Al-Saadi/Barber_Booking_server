
from database.database_conn import get_connection, release_connection


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