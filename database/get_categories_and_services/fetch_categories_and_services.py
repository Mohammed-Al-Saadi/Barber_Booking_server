

from datetime import timedelta
import traceback
from database.database_conn import get_connection, release_connection


def fetch_categories_and_services():
    """
    Fetch all categories and their corresponding services, including the estimated time and prices for each barber, from the database.

    Returns:
    - A dictionary where each key is a category name, and the value is a list of services for that category.
    - Each service includes its ID, name, description, estimated time in minutes, and a list of barbers with their respective prices.
    - Returns None if an error occurs.
    """
    conn = get_connection()
    if not conn:
        print("Failed to connect to the database")
        return None

    try:
        cursor = conn.cursor()

        # Updated SQL query to fetch categories, services, and barber prices
        query = """
            SELECT c.category_name, s.service_id, s.service_name, s.description, s.estimated_time,
                   b.barber_id, b.name AS barber_name, s.price
            FROM Categories c
            JOIN Services s ON c.category_id = s.category_id
            JOIN BarberServicePrices bsp ON s.service_id = bsp.service_id
            JOIN Barbers b ON bsp.barber_id = b.barber_id
            ORDER BY c.category_name, s.service_name, b.name;
        """
        cursor.execute(query)

        # Fetch results
        results = cursor.fetchall()

        # Organize results into a dictionary
        categories_services = {}
        for category_name, service_id, service_name, description, estimated_time, barber_id, barber_name, price in results:
            if category_name not in categories_services:
                categories_services[category_name] = []

            # Find or create the service entry in the list
            service_entry = next((s for s in categories_services[category_name] if s['service_id'] == service_id), None)
            if not service_entry:
                # Convert estimated_time (assumed to be a timedelta) to minutes
                estimated_time_minutes = None
                if isinstance(estimated_time, timedelta):
                    estimated_time_minutes = int(estimated_time.total_seconds() / 60)

                service_entry = {
                    "service_id": service_id,
                    "service_name": service_name,
                    "description": description,
                    "estimated_time": estimated_time_minutes,  # Store time in minutes
                    "price": price  # List to hold barber details
                }
                categories_services[category_name].append(service_entry)



        # Close the cursor and release the connection
        cursor.close()
        release_connection(conn)
        print("Connection released successfully.")
        
        return categories_services

    except Exception as e:
        print(f"Error occurred while fetching categories and services: {e}")
        traceback.print_exc()
        release_connection(conn)
        return None

