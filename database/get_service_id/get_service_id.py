from database.database_conn import get_connection, release_connection


def get_service_id(service_names):
    """
    Fetch the service IDs for a list of service names.

    Parameters:
    - service_names (list): A list of service names (e.g., ["Koko paketti", "Perus hiustenleikkuu"]).

    Returns:
    - list: A list of service IDs corresponding to the service names. 
            If a service is not found, it will be excluded from the list.
    """
    conn = get_connection()
    if not conn:
        print("Failed to connect to the database")
        return None
    
    try:
        cur = conn.cursor()
        # Convert the list of service names into a tuple for the SQL IN clause
        service_names_tuple = tuple(service_names)

        # Query to get the service IDs based on the service names
        cur.execute("""
            SELECT service_id FROM Services
            WHERE service_name IN %s
        """, (service_names_tuple,))  # Using IN clause for multiple service names

        results = cur.fetchall()
        cur.close()

        # Extract service IDs from the results
        service_ids = [result[0] for result in results]  # Create a list of service IDs

        return service_ids

    except Exception as e:
        print(f"Error occurred while fetching the service IDs: {e}")
        return None

    finally:
        # Release the connection back to the pool
        release_connection(conn)
from datetime import datetime