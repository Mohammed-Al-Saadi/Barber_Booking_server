
from datetime import datetime, timedelta

from database.database_conn import get_connection, release_connection

def round_up_to_next_15_minutes(dt):
    """
    Round a datetime object up to the next 15-minute interval.
    """
    if dt.minute % 15 == 0:
        return dt
    else:
        return dt + timedelta(minutes=(15 - dt.minute % 15))

import datetime
from datetime import timedelta, datetime

def round_up_to_next_15_minutes(dt):
    """
    Rounds the time to the next 15-minute interval.
    """
    discard = timedelta(minutes=dt.minute % 15, seconds=dt.second, microseconds=dt.microsecond)
    return dt + (timedelta(minutes=15) - discard)

def get_available_free_slots(barber_id, date):
    """
    Fetch available free time slots for a barber on a specific date, considering
    service arrays in bookings (both main and extra services).

    Parameters:
    - barber_id (int): The ID of the barber.
    - date (datetime.date or str): The date for which to check availability.

    Returns:
    - List of available time slots in "HH:MM" format.
    """
    # Ensure that date is a datetime.date object
    if isinstance(date, str):
        try:
            date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError as e:
            print(f"Error parsing date: {e}")
            return []

    # Get the current time
    now = datetime.now()

    conn = get_connection()
    if not conn:
        print("Failed to connect to the database")
        return []

    try:
        cursor = conn.cursor()

        # 1. Fetch the barber's working hours from BarberSchedules
        cursor.execute("""
            SELECT start_time, end_time 
            FROM BarberSchedules 
            WHERE barber_id = %s
        """, (barber_id,))
        schedule = cursor.fetchone()

        if not schedule:
            print(f"No schedule found for barber ID {barber_id}")
            return []

        start_time, end_time = schedule
        start_time = datetime.combine(date, start_time)
        end_time = datetime.combine(date, end_time)

        # If the date is today, adjust the start time to be at least the current time
        if date == now.date() and start_time < now:
            start_time = now

        # Round start_time to the next nearest 15-minute interval
        start_time = round_up_to_next_15_minutes(start_time)

        # 2. Fetch barber's breaks for the specific date
        cursor.execute("""
            SELECT break_time 
            FROM BarberBreaks
            WHERE barber_id = %s AND break_date = %s
        """, (barber_id, date))
        breaks = cursor.fetchall()

        # Convert the fetched break times into datetime objects
        break_times = [datetime.combine(date, break_time[0]) for break_time in breaks]

        # 3. Fetch existing bookings for the barber on the specified date, including extra services
        cursor.execute("""
            SELECT appointment_time, s.estimated_time, b.extra
            FROM Bookings b
            JOIN Services s ON b.service_id = s.service_id
            WHERE b.barber_id = %s AND DATE(b.appointment_time) = %s
        """, (barber_id, date))
        bookings = cursor.fetchall()

        booked_slots = []
        for appointment_time, estimated_time, extra_services in bookings:
            booking_start = appointment_time
            total_estimated_time = estimated_time

            # If there are extra services, fetch their estimated times and add them
            if extra_services:
                extra_service_ids = tuple(extra_services)  # assuming extra_services is an array of service IDs
                if extra_service_ids:  # ensure extra_service_ids is not empty
                    cursor.execute("""
                        SELECT estimated_time
                        FROM Services
                        WHERE service_id IN %s
                    """, (extra_service_ids,))
                    extra_times = cursor.fetchall()

                    # Add the estimated times of all extra services
                    for extra_time in extra_times:
                        total_estimated_time += extra_time[0]  # Assuming extra_time is a timedelta

            booking_end = booking_start + total_estimated_time
            booked_slots.append((booking_start, booking_end))

        # 4. Generate time slots in increments (e.g., every 15 minutes)
        current_time = start_time
        available_slots = []

        # Adjust the condition to ensure the last slot is included
        while current_time < end_time:
            slot_end_time = current_time + timedelta(minutes=15)

            # Debugging: print the current slot being checked
            print(f"Checking slot: {current_time.strftime('%H:%M')} - {slot_end_time.strftime('%H:%M')}")

            # Check if the time slot overlaps with any booked slots
            overlap = False
            for booking_start, booking_end in booked_slots:
                print(f"Comparing with booking: {booking_start.strftime('%H:%M')} - {booking_end.strftime('%H:%M')}")
                if (current_time < booking_end) and (slot_end_time > booking_start):
                    print(f"Overlap with booking {booking_start.strftime('%H:%M')} - {booking_end.strftime('%H:%M')}")
                    overlap = True
                    break

            # Check if the time slot overlaps with any break slots
            for break_time in break_times:
                print(f"Comparing with break: {break_time.strftime('%H:%M')}")
                if (current_time <= break_time < slot_end_time) or (break_time <= current_time < break_time + timedelta(minutes=15)):
                    print(f"Overlap with break at {break_time.strftime('%H:%M')}")
                    overlap = True
                    break

            # Only add slots that are in the future (from the current time onwards) and have no overlaps
            if not overlap and current_time >= now:
                available_slots.append(current_time.strftime('%H:%M'))

            current_time += timedelta(minutes=15)

        # Close the cursor and connection
        cursor.close()
        release_connection(conn)

        return available_slots

    except Exception as e:
        print(f"Error occurred while fetching available slots: {e}")
        if conn:
            release_connection(conn)
        return []



