
import traceback
from database.database_conn import get_connection, release_connection


def update_booking_price(booking_id, new_price):
    """
    Update the price of a booking in the Bookings table.

    Parameters:
    - booking_id (int): The ID of the booking to be updated.
    - new_price (float): The new price to set for the booking.

    Returns:
    - A tuple (success, message), where success is a boolean indicating if the price was updated,
      and message is a string indicating the result.
    """
    conn = get_connection()
    if not conn:
        print("Failed to connect to the database")
        return False, "Failed to connect to the database."

    try:
        cursor = conn.cursor()

        # Check if the booking exists
        check_query = """
            SELECT COUNT(*) FROM Bookings WHERE booking_id = %s;
        """
        cursor.execute(check_query, (booking_id,))
        (booking_exists,) = cursor.fetchone()

        if booking_exists == 0:
            print(f"Booking ID {booking_id} does not exist.")
            cursor.close()
            release_connection(conn)
            return False, "Booking ID does not exist."

        # SQL query to update the price for the booking
        update_query = """
            UPDATE Bookings
            SET price = %s
            WHERE booking_id = %s;
        """
        # Execute the query with the new price and booking ID
        cursor.execute(update_query, (new_price, booking_id))

        # Commit the transaction
        conn.commit()
        print(f"Price updated successfully for booking ID {booking_id}.")

        # Close the cursor and release the connection
        cursor.close()
        release_connection(conn)
        print("Connection released successfully.")
        
        return True, "Booking price updated successfully."

    except Exception as e:
        print(f"Error occurred while updating booking price: {e}")
        traceback.print_exc()
        release_connection(conn)
        return False, "An error occurred while updating the booking price."