
from database.database_conn import get_connection, release_connection


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
