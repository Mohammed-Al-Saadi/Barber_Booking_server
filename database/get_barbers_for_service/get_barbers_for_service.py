
from datetime import  timedelta
from database.database_conn import get_connection, release_connection


def get_barbers_for_service(service_names):
    """Get all barbers and the total estimated time for the list of services."""
    conn = get_connection()  # Use get_connection() to get a connection from the pool

    if conn:
        try:
            cursor = conn.cursor()

            # Create a query that accepts multiple service names using the IN clause
            query = f"""
                SELECT DISTINCT s.service_name, s.estimated_time, b.barber_id, b.name
                FROM Barbers b
                JOIN BarberServices bs ON b.barber_id = bs.barber_id
                JOIN Services s ON bs.service_id = s.service_id
                WHERE s.service_name IN %s;
            """

            # Format the service names as a tuple to pass it to the query
            service_names_tuple = tuple(service_names)

            # Execute the query
            cursor.execute(query, (service_names_tuple,))

            # Fetch the results
            results = cursor.fetchall()

            # Close the cursor and release the connection
            cursor.close()
            release_connection(conn)

            # If there are no results, return an empty response
            if not results:
                return None

            # Initialize a set for unique barbers and calculate the total estimated time for all services
            barbers = {}
            total_estimated_time = 0  # Initialize total time for all services
            seen_services = set()  # To ensure we only sum the time for each service once

            for row in results:
                service_name = row[0]
                estimated_time = row[1].total_seconds() / 60 if isinstance(row[1], timedelta) else row[1]
                barber_id = row[2]
                barber_name = row[3]

                # Add the barber to the dictionary if they aren't already there
                if barber_id not in barbers:
                    barbers[barber_id] = barber_name

                # Accumulate the estimated time for distinct services only
                if service_name not in seen_services:
                    total_estimated_time += estimated_time
                    seen_services.add(service_name)

            # Convert the dictionary of barbers to a list
            barbers_list = [{"barber_id": barber_id, "name": name} for barber_id, name in barbers.items()]

            # Return all barbers and the total estimated time for the services
            return {
                "barbers": barbers_list,
                "estimated_time": total_estimated_time  # Total time for all distinct services
            }

        except Exception as e:
            release_connection(conn)
            print(f"Error occurred: {e}")
            return None
    else:
        print("Failed to connect to the database")
        return None

