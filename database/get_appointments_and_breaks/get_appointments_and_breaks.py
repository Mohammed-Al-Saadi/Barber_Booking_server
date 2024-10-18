from datetime import timedelta

from database.database_conn import get_connection, release_connection

def get_appointments_and_breaks(barber_id, selected_date):
    """
    Fetch appointment times from the bookings table, break date/time and type from the barberbreaks table,
    start/end time from the BarberSchedules table, and exception times from BarberExceptions.

    Parameters:
    - barber_id (int): The ID of the barber.
    - selected_date (datetime.date): The date for which to fetch appointments.
    
    Returns:
    - List of dictionaries containing separate date and time for appointments, breaks (as a list),
      the final start_time and end_time, and calculated appointment end time.
    """
    conn = get_connection()  # Assuming you have a function to get the database connection
    if not conn:
        print("Failed to connect to the database")
        return []

    try:
        cursor = conn.cursor()

        # SQL query to fetch appointments, breaks, schedules, exceptions, and services
        query = """
            SELECT 
                b.appointment_time, 
                b.service_id,
                b.extra,
                bb.break_date, 
                bb.break_time,
                bb.type AS break_type,
                bs.start_time, 
                bs.end_time,
                be.exception_date, 
                be.custom_start_time, 
                be.custom_end_time, 
                be.is_off,
                s.estimated_time AS primary_estimated_time
            FROM 
                bookings b
            LEFT JOIN 
                barberbreaks bb ON b.barber_id = bb.barber_id
            JOIN 
                BarberSchedules bs ON b.barber_id = bs.barber_id
            LEFT JOIN 
                BarberExceptions be ON b.barber_id = be.barber_id AND DATE(b.appointment_time) = be.exception_date
            JOIN 
                Services s ON b.service_id = s.service_id
            WHERE 
                b.barber_id = %s AND DATE(b.appointment_time) = %s;
        """
        cursor.execute(query, (barber_id, selected_date))
        results = cursor.fetchall()

        appointments_dict = {}

        # Loop through the query result
        for row in results:
            appointment_time, service_id, extra, break_date, break_time, break_type, start_time, end_time, exception_date, custom_start_time, custom_end_time, is_off, primary_estimated_time = row

            # Ensure primary_estimated_time is an integer representing minutes
            if isinstance(primary_estimated_time, timedelta):
                primary_estimated_time = int(primary_estimated_time.total_seconds() // 60)

            # Format the final start and end time based on the exception or regular schedule
            if exception_date and not is_off:
                final_start_time = custom_start_time.strftime('%H:%M:%S') if custom_start_time else start_time.strftime('%H:%M:%S')
                final_end_time = custom_end_time.strftime('%H:%M:%S') if custom_end_time else end_time.strftime('%H:%M:%S')
            else:
                final_start_time = start_time.strftime('%H:%M:%S')
                final_end_time = end_time.strftime('%H:%M:%S')

            # Split the appointment_time into date and time
            appointment_date = appointment_time.strftime('%Y-%m-%d')
            appointment_only_time = appointment_time.strftime('%H:%M:%S')

            # Calculate the total estimated time
            total_estimated_time = primary_estimated_time  # Start with the primary service time

            # If there are extra services, calculate the estimated time for each
            if extra and isinstance(extra, list):  # Check if 'extra' is a list
                extra_service_ids = tuple(map(int, extra))  # Convert the extra services to integers
                if extra_service_ids:
                    extra_services_query = """
                        SELECT SUM(estimated_time)
                        FROM Services
                        WHERE service_id IN %s;
                    """
                    cursor.execute(extra_services_query, (extra_service_ids,))
                    extra_estimated_time = cursor.fetchone()[0] or 0

                    # Ensure extra_estimated_time is treated as an integer
                    if isinstance(extra_estimated_time, timedelta):
                        extra_estimated_time = int(extra_estimated_time.total_seconds() // 60)

                    total_estimated_time += extra_estimated_time

            # Calculate the appointment end time by adding the total estimated time (in minutes) to the appointment start time
            appointment_end_time = appointment_time + timedelta(minutes=total_estimated_time)

            # Group the appointments by appointment_date
            if appointment_date not in appointments_dict:
                appointments_dict[appointment_date] = {
                    "date": appointment_date,
                    "appointments": []
                }

            # Check if this appointment already exists (use time as a key)
            existing_appointment = next(
                (a for a in appointments_dict[appointment_date]["appointments"] if a["appointment_time"] == appointment_only_time), None
            )

            if not existing_appointment:
                # Add this appointment to the list
                appointments_dict[appointment_date]["appointments"].append({
                    "appointment_time": appointment_only_time,
                    "appointment_end_time": appointment_end_time.strftime('%H:%M:%S'),  # Convert end time to a string
                    "breaks": [],
                    "start_time": final_start_time,
                    "end_time": final_end_time,
                    "is_off": is_off
                })
                existing_appointment = appointments_dict[appointment_date]["appointments"][-1]

            # If there's a break, append it to the current appointment's "breaks" list
            if break_date and break_time and break_type:
                existing_appointment["breaks"].append({
                    "break_date": break_date.strftime('%Y-%m-%d'),
                    "break_time": break_time.strftime('%H:%M:%S'),
                    "break_type": break_type
                })

        cursor.close()
        release_connection(conn)

        # Return the grouped appointments with date and time split, and calculated appointment end time
        return list(appointments_dict.values())

    except Exception as e:
        print(f"Error occurred while fetching data for barber {barber_id}: {e}")
        release_connection(conn)
        return []