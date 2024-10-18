
from database.database_conn import get_connection, release_connection


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
