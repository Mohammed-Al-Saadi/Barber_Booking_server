

from datetime import datetime
import traceback

from database.database_conn import get_connection, release_connection

def insert_booking(barber_id, service_id, customer_name, appointment_time, email, phone, price, extra):
    """
    Insert a new booking into the Bookings table.

    Parameters:
    - barber_id (int): The ID of the barber.
    - service_id (int): The ID of the service.
    - customer_name (str): The name of the customer.
    - appointment_time (datetime): The appointment time.
    - email (str): The email address of the customer.
    - phone (str): The phone number of the customer.

    Returns:
    - A tuple (success, message), where success is a boolean indicating if the booking was inserted,
      and message is a string indicating the result.
    """
    conn = get_connection()
    if not conn:
        print("Failed to connect to the database")
        return False, "Failed to connect to the database."

    try:
        cursor = conn.cursor()

        # Check if there is an existing booking for the barber at the same time
        check_query = """
            SELECT COUNT(*) FROM Bookings
            WHERE barber_id = %s AND appointment_time = %s;
        """
        cursor.execute(check_query, (barber_id, appointment_time))
        (existing_bookings,) = cursor.fetchone()

        if existing_bookings > 0:
            print(f"Barber {barber_id} is already booked at {appointment_time}.")
            cursor.close()
            release_connection(conn)
            return False, "Time slot unavailable. Choose another time."

        # SQL query to insert a new booking
        insert_query = """
            INSERT INTO Bookings (barber_id, service_id, customer_name, appointment_time, email, phone, price, extra)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        # Execute the query with provided data
        cursor.execute(insert_query, (barber_id, service_id, customer_name, appointment_time, email, phone, price, extra))
        
        # Commit the transaction
        conn.commit()
        print("Booking inserted successfully.")

        # Close the cursor and release the connection
        cursor.close()
        release_connection(conn)
        print("Connection released successfully.")
        
        return True, "Booking created successfully."

    except Exception as e:
        print(f"Error occurred while inserting booking: {e}")
        traceback.print_exc()
        release_connection(conn)
        return False, "An error occurred while creating the booking."

